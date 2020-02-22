from manimlib.scene.scene import Scene
from manimlib.constants import *
import copy
import itertools as it
from collections import defaultdict, OrderedDict
from manimlib.web.utils import (
    serialize_mobject,
    serialize_animation,
    serialize_wait,
    mobject_serialization_diff,
    get_animated_mobjects,
    get_unserialized_transformations,
    reset_data,
    diff_list_contains_mobject_name,
)
from manimlib.mobject.mobject import Mobject, Group
from manimlib.mobject.svg.tex_mobject import (
    TexMobject,
    TextMobject,
    SingleStringTexMobject,
)
import manimlib.web.utils


class WebScene(Scene):
    def __init__(self, **kwargs):
        self.render_kwargs = kwargs
        # A list of Mobject diffs representing changes made outside of
        # Animations.
        self.scene_diffs = []
        # A list of Mobject diffs representing changes made by Animations.
        self.animation_diffs = []
        # A list of serializations of the Animations that were played.
        self.animation_info_list = []
        reset_data()

    def render(self):
        # Regular Scenes render upon instantiation.
        return super(WebScene, self).__init__(**self.render_kwargs)

    def play(self, *args, **kwargs):
        self.animation_info_list.append(serialize_animation(args[0]))
        self.scene_diffs.append(self.compute_diff())
        super(WebScene, self).play(*args, **kwargs)
        self.animation_diffs.append(self.compute_diff())

    def wait(self, duration=DEFAULT_WAIT_TIME, stop_condition=None):
        self.animation_info_list.append(serialize_wait(duration, stop_condition))
        self.scene_diffs.append(self.compute_diff())
        super(WebScene, self).wait(duration=duration, stop_condition=stop_condition)
        self.animation_diffs.append(self.compute_diff())

    def compute_diff(self):
        ret = {}
        mobject_diffs = {}
        for mob_id, mob in manimlib.web.utils.current_mobjects.items():
            prior_serialization = manimlib.web.utils.prior_mobject_serializations[mob_id]
            current_serialization = serialize_mobject(mob, added=mob in self.mobjects)
            diff = mobject_serialization_diff(
                prior_serialization,
                current_serialization,
            )
            if diff:
                if hasattr(mob, "delegate_for_original") and mob.delegate_for_original:
                    current_diff = mobject_diffs.get(id(mob.original), {})
                    current_diff.update(diff)
                    mobject_diffs[id(mob.original)] = current_diff
                else:
                    mobject_diffs[mob_id] = diff
            manimlib.web.utils.prior_mobject_serializations[mob_id] = current_serialization
        if mobject_diffs:
            ret["mobjects"] = mobject_diffs
        ret["transformations"] = get_unserialized_transformations()
        return ret

    """
    Filters Mobjects that are neither transformed nor added to the Scene from
    self.initial_mobject_serializations.
    """
    def filter_initial_mobject_serializations(self):
        to_delete = []
        for mobject_name in self.initial_mobject_serializations.keys():
            if not diff_list_contains_mobject_name(self.scene_diffs, mobject_name) and \
                    not diff_list_contains_mobject_name(self.animation_diffs, mobject_name):
                to_delete.append(mobject_name)
        for mobject_name in to_delete:
            del self.initial_mobject_serializations[mobject_name]

    def tear_down(self):
        self.initial_mobject_serializations = \
                manimlib.web.utils.rename_initial_mobject_serializations()
        self.scene_diffs = manimlib.web.utils.rename_diffs(self.scene_diffs)
        self.animation_diffs = manimlib.web.utils.rename_diffs(self.animation_diffs)
        self.filter_initial_mobject_serializations();
        self.animation_info_list = manimlib.web.utils.rename_animation_info_list(self.animation_info_list)
        return super(WebScene, self).tear_down()
