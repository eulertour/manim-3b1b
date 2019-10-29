from manimlib.scene.scene import Scene
from manimlib.constants import *
import copy


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

    def get_tex_strings(self):
        return self.TEX_STRINGS

    def get_text_strings(self):
        return self.TEXT_STRINGS

    def render(self):
        # Regular Scenes render upon instantiation.
        return super(WebScene, self).__init__(**self.render_kwargs)

    def play(self, *args, **kwargs):
        print(f"play({args}, {kwargs})")
        play_args = (self, args, kwargs)
        self.render_list.append(copy.deepcopy(play_args))
        super(WebScene, self).play(*args, **kwargs)

    def wait(self, duration=DEFAULT_WAIT_TIME, stop_condition=None):
        wait_args = (self, duration, stop_condition)
        self.render_list.append(copy.deepcopy(wait_args))
        super(WebScene, self).wait(duration=duration, stop_condition=stop_condition)

    def step(self, elapsed_ms, canvas_id):
        elapsed_seconds = elapsed_ms / 1000
        # TODO: super() isn't always necessary
        def render_finished():
            if self.handling_animation is None:
                return True
            if elapsed_seconds > self.current_animations_list_end_time:
                return True
            elif self.handling_animation is False and \
                self.current_wait_stop_condition is not None:
                return self.current_wait_stop_condition()

        while render_finished():
            # finish the previous animation
            if 0 <= self.render_index < len(self.render_list) and \
                self.current_animations_list is not None:
                super(WebScene, self.current_scene_snapshot).finish_animations(self.current_animations_list)

            # check finish condition
            self.render_index += 1
            if self.render_index >= len(self.render_list):
                return False

            # begin the next animation
            render_snapshot_copy = copy.deepcopy(self.render_list[self.render_index])
            self.handling_animation = type(render_snapshot_copy[1]) is tuple
            if self.handling_animation:
                self.current_scene_snapshot, args, kwargs = render_snapshot_copy
                self.current_animations_list = super(
                    WebScene,
                    self.current_scene_snapshot
                ).compile_play_args_to_animation_list(*args, **kwargs)
                super(WebScene, self.current_scene_snapshot).begin_animations(self.current_animations_list)
                self.current_animations_list_start_time = self.current_animations_list_end_time
                self.current_animations_list_end_time += np.max([
                    animation.run_time for animation in self.current_animations_list
                ])
            else:
                self.current_scene_snapshot, \
                self.current_wait_duration, \
                self.current_wait_stop_condition = render_snapshot_copy

                self.current_animations_list = None
                self.current_animations_list_start_time = self.current_animations_list_end_time
                self.current_animations_list_end_time += self.current_wait_duration

            self.current_animations_list_last_t = 0

        # get a frame
        dt = elapsed_seconds - self.current_animations_list_last_t
        if self.handling_animation:
            for animation in self.current_animations_list:
                animation.update_mobjects(dt)
                alpha = (elapsed_seconds - self.current_animations_list_start_time) / animation.run_time
                animation.interpolate(alpha)
        super(WebScene, self.current_scene_snapshot).update_mobjects(dt)
        super(WebScene, self.current_scene_snapshot).update_frame(canvas_id=canvas_id)

        return True # not finished

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
