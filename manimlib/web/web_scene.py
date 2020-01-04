from manimlib.scene.scene import Scene
from manimlib.constants import *
import copy
import itertools as it
from manimlib.web.utils import (
    animation_to_json,
    wait_to_json,
    scene_mobjects_to_json,
    mobject_to_json,
    serialize_mobject,
    mobject_serialization_diff,
    get_mobject_hierarchies_from_scene,
    get_animated_mobjects,
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

        self.initial_mobject_serializations = {}
        self.current_mobject_serializations = {}
        self.scene_diffs = []
        self.animation_diffs = []

    def render(self):
        # Regular Scenes render upon instantiation.
        return super(WebScene, self).__init__(**self.render_kwargs)

    def play(self, *args, **kwargs):
        animation = args[0]

        self.scene_diffs.append(self.compute_diff(next_animation=animation))

        if animation.__class__.__name__.startswith("ApplyPointwiseFunction"):
            self.update_initial_mobject_dict(mobject_list=[animation.mobject])
        else:
            self.update_initial_mobject_dict(mobject_list=animation.get_args())
        self.scenes_before_animation.append(scene_mobjects_to_json(self.mobjects))
        self.animation_list.append(animation_to_json(args, kwargs))
        super(WebScene, self).play(*args, **kwargs)

        self.animation_diffs.append(self.compute_diff())

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

    def compute_diff(self, next_animation=None):
        new_mobject_serializations = {
            id(mob): serialize_mobject(mob, added=mob in self.mobjects)
            for mob in get_mobject_hierarchies_from_scene(self)
        }
        for mob_id in new_mobject_serializations:
            if mob_id not in self.initial_mobject_serializations:
                self.initial_mobject_serializations[mob_id] = copy.deepcopy(new_mobject_serializations[mob_id])
        return self.diff_new_serializations(
            new_mobject_serializations,
            animation_mobjects=get_animated_mobjects(next_animation) if next_animation is not None else None,
        )

    def diff_new_serializations(self, new_serializations, animation_mobjects=None):
        ret = {}
        if animation_mobjects is not None:
            for animation_mobject in animation_mobjects:
                mob_id = id(animation_mobject)
                if mob_id not in self.current_mobject_serializations:
                    # This Mobject hasn't been seen before.
                    self.initial_mobject_serializations[mob_id] = serialize_mobject(animation_mobject)
                elif self.current_mobject_serializations[mob_id]["added"] == False:
                    # This Mobject may have been changed offscreen.
                    ret[id(animation_mobject)] = serialize_mobject(animation_mobject)
        for mob_id in self.current_mobject_serializations:
            prior_serialization = self.current_mobject_serializations[mob_id]
            if prior_serialization["added"] and mob_id not in new_serializations:
                # Mobject was removed.
                ret[mob_id] = {"added": (True, False)}
                self.current_mobject_serializations[mob_id]["added"] = False
            elif mob_id in new_serializations:
                diff = mobject_serialization_diff(
                    prior_serialization,
                    new_serializations[mob_id],
                )
                if diff:
                    ret[mob_id] = diff
                self.current_mobject_serializations[mob_id] = copy.deepcopy(new_serializations[mob_id])
        for mob_id in new_serializations:
            if mob_id not in self.current_mobject_serializations:
                # This is the first time this Mobject appears in the scene,
                # though it may have been modified by an animation.
                diff = mobject_serialization_diff(
                    self.initial_mobject_serializations[mob_id],
                    new_serializations[mob_id],
                )
                if diff:
                    ret[mob_id] = diff
                self.current_mobject_serializations[mob_id] = copy.deepcopy(new_serializations[mob_id])
        return ret
