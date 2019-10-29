from functools import reduce
import itertools as it
import operator as op
import time
import copy

import numpy as np

from manimlib.constants import *
from manimlib.mobject.types.image_mobject import AbstractImageMobject
from manimlib.mobject.mobject import Mobject
from manimlib.mobject.types.point_cloud_mobject import PMobject
from manimlib.mobject.types.vectorized_mobject import VMobject
from manimlib.utils.color import color_to_int_rgba
from manimlib.utils.config_ops import digest_config
from manimlib.utils.images import get_full_raster_image_path
from manimlib.utils.iterables import batch_by_property
from manimlib.utils.iterables import list_difference_update
from manimlib.utils.iterables import remove_list_redundancies
from manimlib.utils.simple_functions import fdiv
from manimlib.utils.space_ops import angle_of_vector
from manimlib.utils.space_ops import get_norm


class Camera(object):
    CONFIG = {
        "background_image": None,
        "pixel_height": DEFAULT_PIXEL_HEIGHT,
        "pixel_width": DEFAULT_PIXEL_WIDTH,
        "frame_rate": DEFAULT_FRAME_RATE,
        # Note: frame height and width will be resized to match
        # the pixel aspect ratio
        "frame_height": FRAME_HEIGHT,
        "frame_width": FRAME_WIDTH,
        "frame_center": ORIGIN,
        "background_color": BLACK,
        "background_opacity": 1,
        # Points in vectorized mobjects with norm greater
        # than this value will be rescaled.
        "max_allowable_norm": FRAME_WIDTH,
        "image_mode": "RGBA",
        "n_channels": 4,
        "pixel_array_dtype": 'uint8',
        # z_buff_func is only used if the flag above is set to True.
        # round z coordinate to nearest hundredth when comparring
        "z_buff_func": lambda m: np.round(m.get_center()[2], 2),
        "cairo_line_width_multiple": 0.01,
    }

    def __init__(self, background=None, **kwargs):
        digest_config(self, kwargs, locals())
        self.rgb_max_val = np.iinfo(self.pixel_array_dtype).max
        self.pixel_array_to_cairo_context = {}
        self.init_background()
        self.resize_frame_shape()
        self.reset()

    def __deepcopy__(self, memo):
        # This is to address a strange bug where deepcopying
        # will result in a segfault, which is somehow related
        # to the aggdraw library
        self.canvas = None
        return copy.copy(self)

    def reset_pixel_shape(self, new_height, new_width):
        self.pixel_width = new_width
        self.pixel_height = new_height
        self.init_background()
        self.resize_frame_shape()
        self.reset()

    def get_pixel_height(self):
        return self.pixel_height

    def get_pixel_width(self):
        return self.pixel_width

    def get_frame_height(self):
        return self.frame_height

    def get_frame_width(self):
        return self.frame_width

    def get_frame_center(self):
        return self.frame_center

    def set_frame_height(self, frame_height):
        self.frame_height = frame_height

    def set_frame_width(self, frame_width):
        self.frame_width = frame_width

    def set_frame_center(self, frame_center):
        self.frame_center = frame_center

    def resize_frame_shape(self, fixed_dimension=0):
        """
        Changes frame_shape to match the aspect ratio
        of the pixels, where fixed_dimension determines
        whether frame_height or frame_width
        remains fixed while the other changes accordingly.
        """
        pixel_height = self.get_pixel_height()
        pixel_width = self.get_pixel_width()
        frame_height = self.get_frame_height()
        frame_width = self.get_frame_width()
        aspect_ratio = fdiv(pixel_width, pixel_height)
        if fixed_dimension == 0:
            frame_height = frame_width / aspect_ratio
        else:
            frame_width = aspect_ratio * frame_height
        self.set_frame_height(frame_height)
        self.set_frame_width(frame_width)

    def init_background(self):
        height = self.get_pixel_height()
        width = self.get_pixel_width()
        if self.background_image is not None:
            raise NotImplementedError('not available in javascript')
        else:
            background_rgba = color_to_int_rgba(
                self.background_color, self.background_opacity
            )
            self.background = np.zeros(
                (height, width, self.n_channels),
                dtype=self.pixel_array_dtype
            )
            self.background[:, :] = background_rgba

    def get_pixel_array(self):
        return self.pixel_array

    def convert_pixel_array(self, pixel_array, convert_from_floats=False):
        retval = np.array(pixel_array)
        if convert_from_floats:
            retval = np.apply_along_axis(
                lambda f: (f * self.rgb_max_val).astype(self.pixel_array_dtype),
                2,
                retval
            )
        return retval

    def set_pixel_array(self, pixel_array, convert_from_floats=False):
        converted_array = self.convert_pixel_array(
            pixel_array, convert_from_floats)
        if not (hasattr(self, "pixel_array") and self.pixel_array.shape == converted_array.shape):
            self.pixel_array = converted_array
        else:
            # Set in place
            self.pixel_array[:, :, :] = converted_array[:, :, :]

    def set_background(self, pixel_array, convert_from_floats=False):
        self.background = self.convert_pixel_array(
            pixel_array, convert_from_floats)

    # TODO, this should live in utils, not as a method of Camera
    def make_background_from_func(self, coords_to_colors_func):
        """
        Sets background by using coords_to_colors_func to determine each pixel's color. Each input
        to coords_to_colors_func is an (x, y) pair in space (in ordinary space coordinates; not
        pixel coordinates), and each output is expected to be an RGBA array of 4 floats.
        """

        print("Starting set_background; for reference, the current time is ", time.strftime("%H:%M:%S"))
        coords = self.get_coords_of_all_pixels()
        new_background = np.apply_along_axis(
            coords_to_colors_func,
            2,
            coords
        )
        print("Ending set_background; for reference, the current time is ", time.strftime("%H:%M:%S"))

        return self.convert_pixel_array(new_background, convert_from_floats=True)

    def set_background_from_func(self, coords_to_colors_func):
        self.set_background(
            self.make_background_from_func(coords_to_colors_func))

    def reset(self):
        self.set_pixel_array(self.background)
        return self

    ####

    # TODO, it's weird that this is part of camera.
    # Clearly it should live elsewhere.
    def extract_mobject_family_members(
            self, mobjects,
            only_those_with_points=False):
        if only_those_with_points:
            method = Mobject.family_members_with_points
        else:
            method = Mobject.get_family
        return remove_list_redundancies(list(
            it.chain(*[method(m) for m in mobjects])
        ))

    def get_mobjects_to_display(
            self, mobjects,
            include_submobjects=True,
            excluded_mobjects=None):
        if include_submobjects:
            mobjects = self.extract_mobject_family_members(
                mobjects, only_those_with_points=True,
            )
            if excluded_mobjects:
                all_excluded = self.extract_mobject_family_members(
                    excluded_mobjects
                )
                mobjects = list_difference_update(mobjects, all_excluded)
        return mobjects

    def is_in_frame(self, mobject):
        fc = self.get_frame_center()
        fh = self.get_frame_height()
        fw = self.get_frame_width()
        return not reduce(op.or_, [
            mobject.get_right()[0] < fc[0] - fw,
            mobject.get_bottom()[1] > fc[1] + fh,
            mobject.get_left()[0] > fc[0] + fw,
            mobject.get_top()[1] < fc[1] - fh,
        ])

    def capture_mobject(self, mobject, **kwargs):
        return self.capture_mobjects([mobject], **kwargs)

    def capture_mobjects(self, mobjects, **kwargs):
        mobjects = self.get_mobjects_to_display(mobjects, **kwargs)

        # Organize this list into batches of the same type, and
        # apply corresponding function to those batches
        type_func_pairs = [
            (VMobject, self.display_multiple_vectorized_mobjects),
            (PMobject, self.display_multiple_point_cloud_mobjects),
            (AbstractImageMobject, self.display_multiple_image_mobjects),
            (Mobject, lambda batch, pa: batch),  # Do nothing
        ]

        def get_mobject_type(mobject):
            for mobject_type, func in type_func_pairs:
                if isinstance(mobject, mobject_type):
                    return mobject_type
            raise Exception(
                "Trying to display something which is not of type Mobject"
            )
        batch_type_pairs = batch_by_property(mobjects, get_mobject_type)

        # Display in these batches
        for batch, batch_type in batch_type_pairs:
            # check what the type is, and call the appropriate function
            for mobject_type, func in type_func_pairs:
                if batch_type == mobject_type:
                    func(batch, self.pixel_array)

    # Methods associated with svg rendering

    def display_multiple_vectorized_mobjects(self, vmobjects, pixel_array):
        pass
        # if len(vmobjects) == 0:
        #     return
        # batch_file_pairs = batch_by_property(
        #     vmobjects,
        #     lambda vm: vm.get_background_image_file()
        # )
        # for batch, file_name in batch_file_pairs:
        #     if file_name:
        #         raise NotImplementedError('not available in javascript')
        #     else:
        #         self.display_multiple_non_background_colored_vmobjects(batch, pixel_array)

    def get_stroke_rgbas(self, vmobject, background=False):
        return vmobject.get_stroke_rgbas(background)

    def get_fill_rgbas(self, vmobject):
        return vmobject.get_fill_rgbas()

    # Methods for other rendering

    def display_multiple_point_cloud_mobjects(self, pmobjects, pixel_array):
        for pmobject in pmobjects:
            self.display_point_cloud(
                pmobject,
                pmobject.points,
                pmobject.rgbas,
                self.adjusted_thickness(pmobject.stroke_width),
                pixel_array,
            )

    def display_point_cloud(self, pmobject, points, rgbas, thickness, pixel_array):
        if len(points) == 0:
            return
        pixel_coords = self.points_to_pixel_coords(
            pmobject, points
        )
        pixel_coords = self.thickened_coordinates(
            pixel_coords, thickness
        )
        rgba_len = pixel_array.shape[2]

        rgbas = (self.rgb_max_val * rgbas).astype(self.pixel_array_dtype)
        target_len = len(pixel_coords)
        factor = target_len // len(rgbas)
        rgbas = np.array([rgbas] * factor).reshape((target_len, rgba_len))

        on_screen_indices = self.on_screen_pixels(pixel_coords)
        pixel_coords = pixel_coords[on_screen_indices]
        rgbas = rgbas[on_screen_indices]

        ph = self.get_pixel_height()
        pw = self.get_pixel_width()

        flattener = np.array([1, pw], dtype='int')
        flattener = flattener.reshape((2, 1))
        indices = np.dot(pixel_coords, flattener)[:, 0]
        indices = indices.astype('int')

        new_pa = pixel_array.reshape((ph * pw, rgba_len))
        new_pa[indices] = rgbas
        pixel_array[:, :] = new_pa.reshape((ph, pw, rgba_len))

    def display_multiple_image_mobjects(self, image_mobjects, pixel_array):
        raise NotImplementedError("not available in javascript")

    def adjust_out_of_range_points(self, points):
        if not np.any(points > self.max_allowable_norm):
            return points
        norms = np.apply_along_axis(get_norm, 1, points)
        violator_indices = norms > self.max_allowable_norm
        violators = points[violator_indices, :]
        violator_norms = norms[violator_indices]
        reshaped_norms = np.repeat(
            violator_norms.reshape((len(violator_norms), 1)),
            points.shape[1], 1
        )
        rescaled = self.max_allowable_norm * violators / reshaped_norms
        points[violator_indices] = rescaled
        return points

    def transform_points_pre_display(self, mobject, points):
        # Subclasses (like ThreeDCamera) may want to
        # adjust points futher before they're shown
        if np.any(np.isnan(points)) or np.any(points == np.inf):
            # TODO, print some kind of warning about
            # mobject having invalid points?
            points = np.zeros((1, 3))
        return points

    def points_to_pixel_coords(self, mobject, points):
        points = self.transform_points_pre_display(
            mobject, points
        )
        shifted_points = points - self.get_frame_center()

        result = np.zeros((len(points), 2))
        pixel_height = self.get_pixel_height()
        pixel_width = self.get_pixel_width()
        frame_height = self.get_frame_height()
        frame_width = self.get_frame_width()
        width_mult = pixel_width / frame_width
        width_add = pixel_width / 2
        height_mult = pixel_height / frame_height
        height_add = pixel_height / 2
        # Flip on y-axis as you go
        height_mult *= -1

        result[:, 0] = shifted_points[:, 0] * width_mult + width_add
        result[:, 1] = shifted_points[:, 1] * height_mult + height_add
        return result.astype('int')

    def on_screen_pixels(self, pixel_coords):
        return reduce(op.and_, [
            pixel_coords[:, 0] >= 0,
            pixel_coords[:, 0] < self.get_pixel_width(),
            pixel_coords[:, 1] >= 0,
            pixel_coords[:, 1] < self.get_pixel_height(),
        ])

    def adjusted_thickness(self, thickness):
        # TODO: This seems...unsystematic
        big_sum = op.add(
            PRODUCTION_QUALITY_CAMERA_CONFIG["pixel_height"],
            PRODUCTION_QUALITY_CAMERA_CONFIG["pixel_width"],
        )
        this_sum = op.add(
            self.get_pixel_height(),
            self.get_pixel_width(),
        )
        factor = fdiv(big_sum, this_sum)
        return 1 + (thickness - 1) / factor

    def get_thickening_nudges(self, thickness):
        thickness = int(thickness)
        _range = list(range(-thickness // 2 + 1, thickness // 2 + 1))
        return np.array(list(it.product(_range, _range)))

    def thickened_coordinates(self, pixel_coords, thickness):
        nudges = self.get_thickening_nudges(thickness)
        pixel_coords = np.array([
            pixel_coords + nudge
            for nudge in nudges
        ])
        size = pixel_coords.size
        return pixel_coords.reshape((size // 2, 2))

    # TODO, reimplement using cairo matrix
    def get_coords_of_all_pixels(self):
        # These are in x, y order, to help me keep things straight
        full_space_dims = np.array([
            self.get_frame_width(),
            self.get_frame_height()
        ])
        full_pixel_dims = np.array([
            self.get_pixel_width(),
            self.get_pixel_height()
        ])

        # These are addressed in the same y, x order as in pixel_array, but the values in them
        # are listed in x, y order
        uncentered_pixel_coords = np.indices(
            [self.get_pixel_height(), self.get_pixel_width()]
        )[::-1].transpose(1, 2, 0)
        uncentered_space_coords = fdiv(
            uncentered_pixel_coords * full_space_dims,
            full_pixel_dims)
        # Could structure above line's computation slightly differently, but figured (without much
        # thought) multiplying by frame_shape first, THEN dividing by pixel_shape, is probably
        # better than the other order, for avoiding underflow quantization in the division (whereas
        # overflow is unlikely to be a problem)

        centered_space_coords = (
            uncentered_space_coords - fdiv(full_space_dims, 2)
        )

        # Have to also flip the y coordinates to account for pixel array being listed in
        # top-to-bottom order, opposite of screen coordinate convention
        centered_space_coords = centered_space_coords * (1, -1)

        return centered_space_coords
