from manimlib.scene.scene import Scene
from manimlib.constants import *
import copy
from manimlib.web.utils import animation_to_json, mobjects_in_scene, mobject_to_json


class WebScene(Scene):
    def __init__(self, **kwargs):
        self.scene_list = []
        self.render_list = []
        self.mobject_dict = {}
        self.render_index = -1
        self.current_scene_snapshot = None
        self.current_animations_list = None
        self.current_animations_list_start_time = 0
        self.current_animations_list_end_time = 0
        self.current_animations_list_last_t = 0
        self.current_wait_duration = 0
        self.current_wait_stop_condition = None
        self.handling_animation = None
        self.render_kwargs = kwargs

    def render(self):
        # Regular Scenes render upon instantiation.
        return super(WebScene, self).__init__(**self.render_kwargs)

    def play(self, *args, **kwargs):
        self.update_mobject_dict()
        self.scene_list.append(mobjects_in_scene(self))
        self.render_list.append(animation_to_json(args, kwargs))
        super(WebScene, self).play(*args, **kwargs)

    def wait(self, duration=DEFAULT_WAIT_TIME, stop_condition=None):
        wait_args = (self, duration, stop_condition)
        self.render_list.append(copy.deepcopy(wait_args))
        super(WebScene, self).wait(duration=duration, stop_condition=stop_condition)

    def update_mobject_dict(self):
        for mob in self.mobjects:
            if id(mob) not in self.mobject_dict:
                self.mobject_dict[id(mob)] = mobject_to_json(mob)

    def tear_down(self):
        # convert scene_list to diffs?
        pass
