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
    mobject_serialization_diff,
    get_mobject_hierarchies_from_scene,
    get_mobject_hierarchies_from_mobject_list,
    get_animated_mobjects,
    get_submobjects_for_serialization,
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

        # Keep a count of the number of times each class of Mobject has appeared
        # in the Scene for naming (e.g. Square1, Square2, ...).
        self.mobject_names_to_counts = defaultdict(lambda: 1)
        # A map of Mobject IDs to human-readable names.
        self.mobject_ids_to_names = {}
        # A map of Mobject IDs to serializations of the Mobject as it existed
        # when it was first seen (deprecated).
        self.initial_mobject_serializations = {}
        # A map of Mobject IDs to serializations of the Mobject as it existed
        # when it was last diffed.
        self.current_mobject_serializations = {}
        # A list of Mobject diffs representing changes not made by Animations.
        self.scene_diffs = []
        # A list of Mobject diffs representing changes made by Animations.
        self.animation_diffs = []
        # A list of serializations of the Animations that were played.
        self.animation_info_list = []

    def render(self):
        # Regular Scenes render upon instantiation.
        return super(WebScene, self).__init__(**self.render_kwargs)

    def play(self, *args, **kwargs):
        animation = args[0]
        self.animation_info_list.append(serialize_animation(animation))
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
        new_mobject_serializations = OrderedDict([
            (id(mob), serialize_mobject(mob, added=mob in self.mobjects))
            for mob in get_mobject_hierarchies_from_scene(self)
        ])
        for mob_id in new_mobject_serializations:
            if mob_id not in self.initial_mobject_serializations:
                self.name_mobject(mob_id, new_mobject_serializations[mob_id]["className"])
                self.initial_mobject_serializations[mob_id] = copy.deepcopy(new_mobject_serializations[mob_id])
                # A Mobject must be added by a scene diff or an animation.
                self.initial_mobject_serializations[mob_id]["added"] = False
        return self.diff_new_serializations(
            new_mobject_serializations,
            animation_mobjects=get_animated_mobjects(next_animation) if next_animation is not None else None,
        )

    def name_mobject(self, mob_id, class_name):
        mob_name = f"{class_name}{self.mobject_names_to_counts[class_name]}"
        self.mobject_ids_to_names[mob_id] = mob_name
        self.mobject_names_to_counts[class_name] += 1

    def diff_new_serializations(self, new_serializations, animation_mobjects=None):
        ret = {}
        if animation_mobjects is not None:
            for animation_mobject in animation_mobjects:
                mob_id = id(animation_mobject)
                if mob_id not in self.current_mobject_serializations:
                    # This Mobject hasn't been seen before.
                    animation_mobject_serializations = OrderedDict([
                        (id(mob), serialize_mobject(mob, added=False))
                        for mob in get_submobjects_for_serialization(animation_mobject)
                    ])
                    for mob_id in animation_mobject_serializations:
                        if mob_id not in self.mobject_ids_to_names:
                            self.name_mobject(mob_id, animation_mobject_serializations[mob_id]["className"])
                        if mob_id not in self.initial_mobject_serializations:
                            self.initial_mobject_serializations[mob_id] = copy.deepcopy(animation_mobject_serializations[mob_id])
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

    def rename_diff(self, diff):
        new_diff = copy.deepcopy(diff)
        if "submobjects" in new_diff and new_diff["submobjects"]:
            print(diff)
            print(new_diff)
            starting_submobjects, ending_submobjects = new_diff["submobjects"]
            new_starting_submobjects = list(map(lambda submob_id: self.mobject_ids_to_names[submob_id], starting_submobjects))
            new_ending_submobjects = list(map(lambda submob_id: self.mobject_ids_to_names[submob_id], ending_submobjects))
            new_diff["submobjects"] = (new_starting_submobjects, new_ending_submobjects)
        if "args" in new_diff and new_diff["args"]:
            new_diff["args"] = list(map(lambda submob_id: self.mobject_ids_to_names[submob_id], new_diff["args"]))
        return new_diff

    def rename_diffs(self, diffs):
        new_diffs = []
        for diff in diffs:
            new_diff = {}
            for mob_id in diff:
                new_diff[self.mobject_ids_to_names[mob_id]] = self.rename_diff(diff[mob_id])
            new_diffs.append(new_diff)
        return new_diffs

    def rename_animation_info_list(self):
        new_info = []
        for info in self.animation_info_list:
            animation_class = info["className"]
            args = info["args"]
            config = info["config"]
            new_args = []
            for arg in args:
                if arg in self.mobject_ids_to_names:
                    new_args.append(self.mobject_ids_to_names[arg])
                else:
                    new_args.append(arg)
            new_config = {}
            for key, val in config.items():
                if val in self.mobject_ids_to_names:
                    new_config[key] = self.mobject_ids_to_names[val]
                else:
                    new_config[key] = val
            new_info.append({
                "className": animation_class,
                "args": new_args,
                "config": new_config,
            })
        self.animation_info_list = new_info

    def rename_initial_mobject_serializations(self):
        new_mobject_dict = {}
        for mob_id in self.initial_mobject_serializations:
            new_serialization = self.initial_mobject_serializations[mob_id]
            if "submobjects" in new_serialization:
                new_serialization["submobjects"] = list(map(lambda submob_id: self.mobject_ids_to_names[submob_id], new_serialization["submobjects"]))
            if "args" in new_serialization:
                new_args = []
                for arg in new_serialization["args"]:
                    if arg in self.mobject_ids_to_names:
                        new_args.append(self.mobject_ids_to_names[arg])
                    else:
                        new_args.append(arg)
                new_serialization["args"] = new_args
            new_mobject_dict[self.mobject_ids_to_names[mob_id]] = new_serialization
        self.initial_mobject_serializations = new_mobject_dict

    def tear_down(self):
        self.rename_initial_mobject_serializations()
        self.scene_diffs = self.rename_diffs(self.scene_diffs)
        self.animation_diffs = self.rename_diffs(self.animation_diffs)
        self.rename_animation_info_list()
        return super(WebScene, self).tear_down()
