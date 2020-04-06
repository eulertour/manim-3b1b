from manimlib.scene.scene import PyScene
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
    check_required,
)
from manimlib.mobject.mobject import Mobject, Group
from manimlib.mobject.svg.tex_mobject import (
    TexMobject,
    TextMobject,
    SingleStringTexMobject,
)
import manimlib.web.utils


class Scene(PyScene):
    def __init__(self, **kwargs):
        self.render_kwargs = kwargs
        # A list of Mobject diffs representing changes made outside of
        # Animations.
        self.scene_diffs = []
        # A list of Mobject diffs representing changes made by Animations.
        self.animation_diffs = []
        # A list of serializations of the Animations that were played.
        self.animation_info_list = []
        reset_data(self)

    def render(self):
        # Regular Scenes render upon instantiation.
        return super(Scene, self).__init__(**self.render_kwargs)

    def play(self, *args, **kwargs):
        super(Scene, self).play(*args, **kwargs)

    def wait(self, duration=DEFAULT_WAIT_TIME, stop_condition=None):
        super(Scene, self).wait(duration=duration, stop_condition=stop_condition)

    def dump_frames(self):
        return self.camera.frame_data
