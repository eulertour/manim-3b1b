import copy
from ..utils.family import extract_mobject_family_members
from manim import config
from ..mobject.value_tracker import ValueTracker
from ..mobject.types.vectorized_mobject import VMobject
from ..mobject.types.image_mobject import ImageMobject


class WebGLRenderer:
    def __init__(self):
        self.keyframes = []
        self.previous_scene_index = None
        self.previous_scene = None
        self.camera = WebGLCamera()

        self.skip_animations = True
        self.num_plays = 0

    def get_updated_scene_data(self, request):
        requested_scene_index = request["animation_index"]

        scene_finished = False
        if requested_scene_index == request["end_index"]:
            scene_finished = True

        if (
            request["animation_offset"]
            <= self.keyframes[requested_scene_index].duration
        ):
            animation_offset = request["animation_offset"]
        else:
            if requested_scene_index + 1 < request["end_index"]:
                requested_scene_index += 1
                animation_offset = 0
            else:
                scene_finished = True
                animation_offset = self.keyframes[requested_scene_index].duration

        if requested_scene_index == self.previous_scene_index:
            requested_scene = self.previous_scene
            update_previous_scene = False
        else:
            requested_scene = copy.deepcopy(self.keyframes[requested_scene_index])
            update_previous_scene = True
        requested_scene.update_to_time(animation_offset)

        # Construct the response
        ids_to_remove = []
        mobjects_to_add = []
        animations = []
        updaters = []
        update_data = []

        # TODO: Only remove/add changed mobjects rather than all of them.
        if self.previous_scene is not None and (
            request["first_request"] or self.previous_scene != requested_scene
        ):
            previous_mobjects = extract_mobject_family_members(
                self.previous_scene.mobjects, only_those_with_points=True
            )
            # Remove everything from the previous scene.
            ids_to_remove = [
                mob.original_id
                for mob in previous_mobjects
                if not isinstance(mob, ValueTracker)
            ]

        if request["first_request"] or self.previous_scene != requested_scene:
            # Add everything from the requested scene.
            pass

        return (
            requested_scene,
            requested_scene_index,
            scene_finished,
            animation_offset,
            update_previous_scene,
            ids_to_remove,
            mobjects_to_add,
            animations,
            updaters,
            update_data,
        )

    def init_scene(self, scene):
        pass

    def scene_finished(self, scene):
        pass

    def play(self, scene, *args, **kwargs):
        self.num_plays += 1
        # If the scene contains an updater it must be updated frame by frame.
        for mob in extract_mobject_family_members(scene.mobjects):
            if len(mob.updaters) > 0:
                self.skip_animations = False
                break
        s = scene.compile_animation_data(*args, skip_rendering=True, **kwargs)
        self.skip_animations = True

        scene_copy = copy.deepcopy(scene)
        scene_copy.renderer = self
        self.keyframes.append(scene_copy)
        if s is None:
            # Nothing happens in this animation, so there's no need to update it.
            scene_copy.is_static = True
        else:
            scene_copy.is_static = False
            scene.play_internal(skip_rendering=True)

    def update_frame(  # TODO Description in Docstring
        self,
        scene,
        mobjects=None,
        include_submobjects=True,
        ignore_skipping=True,
        **kwargs,
    ):
        pass

    def save_static_frame_data(self, scene, static_mobjects):
        pass

    def add_frame(self, frame, num_frames=1):
        pass

    def get_frame(self):
        pass


class WebGLCamera:
    def __init__(self, use_z_index=True):
        self.use_z_index = use_z_index
        self.frame_rate = config["webgl_updater_fps"]


def serialize_mobject_to_json(mobject):
    mob_json = {"id": mobject.original_id}

    if isinstance(mobject, VMobject):
        mob_json["type"] = "VMOBJECT"
        needs_redraw = False
        point_hash = hash(tuple(mobject.points.flatten()))
        if mobject.point_hash != point_hash:
            mobject.point_hash = point_hash
            needs_redraw = True
        mob_json["vectorized_mobject_data"]["needs_redraw"] = needs_redraw

        mob_json["vectorized_mobject_data"]["points"] = []
        for point in mobject.points:
            mob_json["vectorized_mobject_data"]["points"].append(
                {"x": point[0], "y": point[1], "z": point[2]}
            )

        mob_style = mobject.get_style(simple=True)
        mob_json["style"]["fill_color"] = mob_style["fill_color"]
        mob_json["style"]["fill_opacity"] = mob_style["fill_opacity"]
        mob_json["style"]["stroke_color"] = mob_style["stroke_color"]
        mob_json["style"]["stroke_opacity"] = mob_style["stroke_opacity"]
        mob_json["style"]["stroke_width"] = mob_style["stroke_width"]
    elif isinstance(mobject, ImageMobject):
        mob_json["type"] = "IMAGE_MOBJECT"
        mob_proto.type = frameserver_pb2.MobjectData.MobjectType.IMAGE_MOBJECT
        mob_style = mobject.get_style()
        mob_proto.style.fill_color = mob_style["fill_color"]
        mob_proto.style.fill_opacity = float(mob_style["fill_opacity"])
        assets_dir_path = str(config.get_dir("assets_dir"))
        if mobject.path.startswith(assets_dir_path):
            mob_proto.image_mobject_data.path = mobject.path[len(assets_dir_path) + 1 :]
        else:
            logger.info(
                f"Expected path {mobject.path} to be under the assets dir ({assets_dir_path})"
            )
        mob_proto.image_mobject_data.height = mobject.get_height()
        mob_proto.image_mobject_data.width = mobject.get_width()
        mob_center = mobject.get_center()
        mob_proto.image_mobject_data.center.x = mob_center[0]
        mob_proto.image_mobject_data.center.y = mob_center[1]
        mob_proto.image_mobject_data.center.z = mob_center[2]
    return mob_proto


def get(input_file_path, scene_name, renderer):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    frameserver_pb2_grpc.add_FrameServerServicer_to_server(
        FrameServer(server, input_file_path, scene_name, renderer), server
    )
    server.add_insecure_port("localhost:50051")
    return server
