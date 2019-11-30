from manimlib.scene.scene import Scene
from manimlib.constants import *
import copy
from manimlib.web.utils import (
    animation_to_json,
    wait_to_json,
    scene_mobjects_to_json,
    mobject_to_json,
)
from manimlib.mobject.mobject import Mobject, Group
from manimlib.mobject.svg.tex_mobject import (
    TexMobject,
    TextMobject,
    SingleStringTexMobject,
)


class WebScene(Scene):
    def __init__(self, **kwargs):
        # A list of snapshots of the Scene before each Animation
        self.scenes_before_animation = []
        # A list of serialized Animations
        self.animation_list = []
        # A mapping of ids to Mobjects
        self.initial_mobject_dict = {}
        self.render_kwargs = kwargs

    def render(self):
        # Regular Scenes render upon instantiation.
        return super(WebScene, self).__init__(**self.render_kwargs)

    def play(self, *args, **kwargs):
        self.update_initial_mobject_dict(mobject_list=args[0].get_args())
        self.scenes_before_animation.append(scene_mobjects_to_json(self.mobjects))
        self.animation_list.append(animation_to_json(args, kwargs))
        super(WebScene, self).play(*args, **kwargs)

    def wait(self, duration=DEFAULT_WAIT_TIME, stop_condition=None):
        self.scenes_before_animation.append(scene_mobjects_to_json(self.mobjects))
        self.animation_list.append(wait_to_json(duration, stop_condition))
        super(WebScene, self).wait(duration=duration, stop_condition=stop_condition)

    def update_initial_mobject_dict(self, mobject_list=None, include_self=True):
        mob_list = [] if mobject_list is None else list(mobject_list)
        if include_self:
            mob_list += self.mobjects
        for mob in mob_list:
            mob_id = id(mob)
            if mob_id not in self.initial_mobject_dict:
                self.initial_mobject_dict[mob_id] = mobject_to_json(mob)
                if type(mob) in [
                    Group,
                    Mobject,
                    TexMobject,
                    TextMobject,
                    SingleStringTexMobject,
                ]:
                    # handle the submobjects
                    self.update_initial_mobject_dict(mobject_list=mob.submobjects, include_self=False)

    def tear_down(self):
        # convert scenes_before_animation to diffs?
        pass
