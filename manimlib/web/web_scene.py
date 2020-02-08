from manimlib.scene.scene import Scene
from manimlib.constants import *
import copy
import itertools as it
from collections import defaultdict, OrderedDict
from manimlib.web.utils import (
    animation_to_json,
    wait_to_json,
    scene_mobjects_to_json,
    mobject_to_json,
    serialize_mobject,
    serialize_animation,
    serialize_wait,
    mobject_serialization_diff,
    get_animated_mobjects,
    get_unserialized_transformations,
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
        for mob_id, mob in manimlib.web.utils.current_mobjects.items():
            prior_serialization = manimlib.web.utils.prior_mobject_serializations[mob_id]
            current_serialization = serialize_mobject(mob, added=mob in self.mobjects)
            diff = mobject_serialization_diff(
                prior_serialization,
                current_serialization,
            )
            if diff:
                ret[mob_id] = diff
            manimlib.web.utils.prior_mobject_serializations[mob_id] = current_serialization
        ret["transformations"] = get_unserialized_transformations()
        return ret

    def tear_down(self):
        self.initial_mobject_serializations = \
                manimlib.web.utils.rename_initial_mobject_serializations()
        self.scene_diffs = manimlib.web.utils.rename_diffs(self.scene_diffs)
        self.animation_diffs = manimlib.web.utils.rename_diffs(self.animation_diffs)
        self.animation_info_list = manimlib.web.utils.rename_animation_info_list(self.animation_info_list)
        return super(WebScene, self).tear_down()
