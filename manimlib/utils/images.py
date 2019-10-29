import numpy as np
import os

from manimlib.utils.file_ops import seek_full_path_from_defaults


def get_full_raster_image_path(image_file_name):
    return seek_full_path_from_defaults(
        image_file_name,
        default_dir=os.path.join("assets", "raster_images"),
        extensions=[".jpg", ".png", ".gif"]
    )


def drag_pixels(frames):
    curr = frames[0]
    new_frames = []
    for frame in frames:
        curr += (curr == 0) * np.array(frame)
        new_frames.append(np.array(curr))
    return new_frames


def invert_image(image):
    raise NotImplementedError('not available in javascript')
