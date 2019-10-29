from manimlib.scene.scene import Scene
from manimlib.constants import *
import copy
from manimlib.web.utils import animation_to_json


class WebScene(Scene):
    def __init__(self, **kwargs):
        self.render_list = []
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
        print(f"play({args}, {kwargs})")
        self.render_list.append(animation_to_json(args, kwargs))

    def wait(self, duration=DEFAULT_WAIT_TIME, stop_condition=None):
        wait_args = (self, duration, stop_condition)
        self.render_list.append(copy.deepcopy(wait_args))
        super(WebScene, self).wait(duration=duration, stop_condition=stop_condition)

    def reset(self):
        self.render_index = -1
        self.current_scene_snapshot = None
        self.current_animations_list = None
        self.current_animations_list_start_time = 0
        self.current_animations_list_end_time = 0
        self.current_animations_list_last_t = 0

    def tear_down(self):
        # compile the play args here?
        pass
