import sys
import collections
import numpy as np
import copy
import itertools as it
if sys.platform == "emscripten":
    import js
    import pyodide
else:
    from manimlib.web.web_mock import tex2points
from collections import defaultdict

past_hierarchy_when_diffed = defaultdict(lambda: collections.defaultdict(list))
# Maps a given Mobject ID to a list of IDs of its past or present parent
# Mobjects that were diffed while it was part of their hierarchy but not
# considered to be required.
past_diffed_parents = defaultdict(list)
# Format string used in place of the Mobject ID for Mobjects that were copied
# from one the user created.
COPIED_MOBJECT_FORMAT = "<copy of {}>"
# String used in place of the Mobject ID for Mobjects that weren't created by
# the user.
UNKNOWN_MOBJECT = "<unknown_mobject>"
# Maps a given Mobject ID to the serialization of the Mobject as it existed
# when it was first created.
initial_mobject_serializations = {}
# Maps a given Mobject ID to the serialization of the Mobject as it existed
# at the latter of when it was created and when it was last diffed.
prior_mobject_serializations = {}
# Maps a given Mobjects ID to the Mobject itself.
current_mobjects = {}
# Maps a given Mobject class to the number of Mobjects of that class that have
# been created.
mobject_class_counts = defaultdict(lambda: 1)
# Maps a given Mobject name to the number of copies of that Mobject that have
# been created.
mobject_copy_counts = defaultdict(lambda: 1)
# Maps a given Mobject ID to a human-readable name for that Mobject.
mobject_ids_to_names = {}
# List of transformations applied to Mobjects in the order they are applied.
transformation_list = []
next_unserialized_transformation_index = 0
web_scene = None

def reset_data(scene):
    global \
        initial_mobject_serializations, \
        prior_mobject_serializations, \
        current_mobjects, \
        mobject_class_counts, \
        mobject_ids_to_names, \
        transformation_list, \
        next_unserialized_transformation_index, \
        web_scene
    initial_mobject_serializations = {}
    prior_mobject_serializations = {}
    current_mobjects = {}
    mobject_class_counts = defaultdict(lambda: 1)
    mobject_ids_to_names = {}
    transformation_list = []
    next_unserialized_transformation_index = 0
    web_scene = scene

def get_unserialized_transformations():
    global next_unserialized_transformation_index
    ret = transformation_list[next_unserialized_transformation_index:]
    next_unserialized_transformation_index = len(transformation_list)
    return ret

def register_transformation(mob, *transformation):
    if hasattr(mob, "delegate_for_original") and mob.delegate_for_original:
        mob_id = id(mob.original)
    else:
        mob_id = id(mob)
    if mob_id not in current_mobjects:
        # This Mobject's registration was skipped, so its registration should be
        # skipped as well.
        return
    check_required(mob_id)
    transformation_list.append((
        len(transformation_list),
        mob_id,
        *transformation,
    ))

def register_mobject(mob, copy_tag=""):
    mob_id = id(mob)
    if mob_id not in current_mobjects:
        current_mobjects[mob_id] = mob
        name_mobject(mob, copy_tag=copy_tag)

    initial_mobject_serializations[mob_id] = serialize_mobject(mob)
    prior_mobject_serializations[mob_id] = \
            copy.deepcopy(initial_mobject_serializations[mob_id])


def name_mobject(mob, copy_tag=""):
    class_name = mob.__class__.__name__
    if hasattr(mob, "original"):
        original_mob_name = mobject_ids_to_names[id(mob.original)]
        tagged_name = original_mob_name + f"#{copy_tag}"
        mob_name = tagged_name + f"{mobject_copy_counts[tagged_name]}"
        mobject_copy_counts[tagged_name] += 1
    else:
        mob_name = f"{class_name}{mobject_class_counts[class_name]}"
        mobject_class_counts[class_name] += 1
    mobject_ids_to_names[id(mob)] = mob_name


def rename_initial_mobject_serializations():
    new_mobject_dict = {}
    for mob_id in initial_mobject_serializations:
        new_serialization = initial_mobject_serializations[mob_id]
        if not initial_mobject_serializations[mob_id]['required']:
            continue
        if "submobjects" in new_serialization:
            new_serialization["submobjects"] = list(map(
                lambda submob_id: mobject_ids_to_names[submob_id],
                new_serialization["submobjects"],
            ))
        if "args" in new_serialization:
            new_args = []
            for arg in new_serialization["args"]:
                if arg in mobject_ids_to_names:
                    new_args.append(mobject_ids_to_names[arg])
                else:
                    new_args.append(arg)
            new_serialization["args"] = new_args
        new_mobject_dict[mobject_ids_to_names[mob_id]] = new_serialization
    return new_mobject_dict


def rename_diff(diff):
    new_diff = copy.deepcopy(diff)
    if "submobjects" in new_diff and new_diff["submobjects"]:
        starting_submobjects, ending_submobjects = new_diff["submobjects"]
        new_starting_submobjects = list(map(lambda submob_id: mobject_ids_to_names[submob_id], starting_submobjects))
        new_ending_submobjects = []
        for submob_id in ending_submobjects:
            if submob_id in mobject_ids_to_names:
                new_ending_submobjects.append(mobject_ids_to_names[submob_id])
            else:
                # The Mobject contains a submobject that wasn't created by the
                # user (e.g. it was created in Mobject.align_submobjects).
                new_ending_submobjects.append(UNKNOWN_MOBJECT)
            new_diff["submobjects"] = (new_starting_submobjects, new_ending_submobjects)
    if "args" in new_diff and new_diff["args"]:
        new_diff["args"] = list(map(lambda submob_id: mobject_ids_to_names[submob_id], new_diff["args"]))
    return new_diff


def rename_diffs(diffs):
    new_diffs = []
    for diff in diffs:
        new_diff = {}
        for attr in diff:
            if attr == "mobjects":
                new_diff["mobjects"] = {}
                for mob_id in diff["mobjects"]:
                    if not initial_mobject_serializations[mob_id]['required']:
                        continue
                    new_diff["mobjects"][mobject_ids_to_names[mob_id]] = rename_diff(diff["mobjects"][mob_id])
            elif attr == "transformations":
                # This is the transformation list. Transformations have the form
                # (index, mob_id, *params) before renaming.
                new_transformations = []
                for transformation in diff[attr]:
                    mob_id = transformation[1]
                    if not initial_mobject_serializations[mob_id]['required']:
                        continue
                    mob_name = mobject_ids_to_names[mob_id]
                    if mob_id in mobject_ids_to_names:
                        new_transformations.append((
                            transformation[0],
                            mob_name,
                            *transformation[2:],
                        ))
                    else:
                        # The scene serialized the transformation of a Mobject
                        # that was neither created by nor copied from the user
                        # (e.g.  a copy of a copy).
                        new_transformations.append((
                            transformation[0],
                            UNKNOWN_MOBJECT,
                            *transformation[2:],
                        ))
                if new_transformations:
                    new_diff["transformations"] = new_transformations
            else:
                print(f"Unknown diff attribute {attr}")
        new_diffs.append(new_diff)
    return new_diffs


def rename_animation_info_list(animation_info_list):
    new_info_list = []
    for animation_group in animation_info_list:
        new_animation_group = []
        for animation in animation_group:
            args = animation["args"]
            config = animation["config"]
            new_args = []
            for arg in args:
                if arg in mobject_ids_to_names:
                    new_args.append(mobject_ids_to_names[arg])
                else:
                    new_args.append(arg)
            new_config = {}
            for key, val in config.items():
                if val in mobject_ids_to_names:
                    new_config[key] = mobject_ids_to_names[val]
                else:
                    new_config[key] = val
            new_animation_group.append({
                "className": animation["className"],
                "args": new_args,
                "config": new_config,
                "runtime": animation["run_time"],
            })
        new_info_list.append(new_animation_group)
    return new_info_list


def serialize_arg(arg):
    from manimlib.mobject.mobject import Mobject
    if isinstance(arg, Mobject):
        return id(arg)
    else:
        return arg

def serialize_args(args):
    return [serialize_arg(arg) for arg in args]

def serialize_config(config):
    return { k: serialize_arg(v) for (k, v) in config.items() }

def pointwise_function_wrapper(func):
    def wrapper(js_point):
        return func(pyodide.as_nested_list(js_point))
    return wrapper

def get_mobject_style(mob):
    return {
        "strokeColor": mob.get_stroke_color().get_hex(),
        "strokeOpacity": mob.get_stroke_opacity(),
        "fillColor": mob.get_fill_color().get_hex(),
        "fillOpacity": mob.get_fill_opacity(),
        "strokeWidth": mob.get_stroke_width(),
    }

def tex_to_points(tex):
    if sys.platform == "emscripten":
        return pyodide.as_nested_list(js.texToPoints(tex))
    else:
        print("searching cache for " + tex)
        return tex2points(tex)

def serialize_animations(animations):
    return [serialize_animation(animation) for animation in animations]

"""
rename_rename_animation_info_list() must be updated in order for changes to
the serialization to be visible.
"""
def serialize_animation(animation):
    return {
        "className": animation.__class__.__name__,
        "args": animation.args,
        "config": animation.config,
        "run_time": animation.run_time,
    }

"""
rename_rename_animation_info_list() must be updated in order for changes to
the serialization to be visible.
"""
def serialize_wait(duration, stop_condition):
    return [{
        "className": "Wait",
        "args": [],
        "config": { "stop_condition": stop_condition },
        "run_time": duration,
    }]

CLASSES_WHOSE_SUBMOBJECT_LIST_IS_NOT_SERIALIZED = [
    "TexMobject",
    "TextMobject",
    "SingleStringTexMobject",
    "DecimalNumber",
]


"""
rename_initial_mobject_serializations() must be updated in order for changes to
the serialization to be visible.
"""
def serialize_mobject(mob, added=False):
    from manimlib.mobject.mobject import Group, Mobject
    from manimlib.mobject.types.vectorized_mobject import VMobject, VGroup
    class_name = mob.__class__.__name__
    ret = {
        "className": class_name,
        "args": copy.deepcopy(mob.args),
        "config": copy.deepcopy(mob.config),
        "added": added,
        "required": False,
    }
    if class_name not in CLASSES_WHOSE_SUBMOBJECT_LIST_IS_NOT_SERIALIZED:
        ret["submobjects"] = [id(mob) for mob in mob.submobjects]
    if isinstance(mob, VMobject):
        # ret["position"] = mob.get_center()
        ret["style"] = get_mobject_style(mob)
    return ret


# ('shift', vector)
def shift_transforms_equal(shift1, shift2):
    assert(shift1[0] == 'shift')
    assert(shift2[0] == 'shift')
    return np.allclose(shift1[1], shift2[1])

# ('rotate', angle, axis)
def rotate_transforms_equal(rotate1, rotate2):
    assert(rotate1[0] == 'rotate')
    assert(rotate1[0] == 'rotate')
    if rotate1[1] != rotate2[1]:
        return False
    if not np.array_equal(rotate1[2], rotate2[2]):
        return False
    return True

# ('scale', factor)
def scale_transforms_equal(scale1, scale2):
    assert(scale1[0] == 'scale')
    assert(scale2[0] == 'scale')
    return scale2[1] == scale2[1]

def transforms_equal(transform1, transform2):
    command1, command2 = transform1[0], transform2[0]
    if command1 != command2:
        return False
    elif command1 == "rotate":
        return rotate_transforms_equal(transform1, transform2)
    elif command1 == "scale":
        return scale_transforms_equal(transform1, transform2)
    elif command1 == "shift":
        return shift_transforms_equal(transform1, transform2)
    else:
        print(f"Failed to determine if {transform1} and {transform2} are equivalent transformations")

def transform_lists_equal(starting_transforms, ending_transforms):
    if len(starting_transforms) != len(ending_transforms):
        return False
    for transform1, transform2 in zip(starting_transforms, ending_transforms):
        if not transforms_equal(transform1, transform2):
            return False
    return True

def mobject_serialization_diff(starting_serialization, ending_serialization):
    ret = {}
    for attr in starting_serialization:
        starting_attr = starting_serialization[attr]
        ending_attr = ending_serialization[attr]
        assert(attr in ending_serialization)
        if attr == "submobjects":
            if set(starting_attr) != set(ending_attr):
                ret[attr] = (starting_attr, ending_attr)
        elif attr == "style":
            style_diff = {}
            for style_attr in [
                "strokeColor",
                "strokeOpacity",
                "fillColor",
                "fillOpacity",
                "strokeWidth",
            ]:
                if starting_attr[style_attr] != ending_attr[style_attr]:
                    style_diff[style_attr] = (starting_attr[style_attr], ending_attr[style_attr])
            if style_diff:
                ret["style"] = style_diff
        elif attr == "config":
            for config_attr in starting_attr:
                assert(config_attr in ending_attr, "Mobject config changed.")
            config_diff = {}
            for config_attr in starting_attr:
                starting_value = starting_attr[config_attr]
                ending_value = ending_attr[config_attr]
                if type(starting_value) == np.ndarray:
                    if not np.allclose(starting_value, ending_value):
                        config_diff[config_attr] = (starting_value, ending_value)
                else:
                    if starting_value != ending_value:
                        config_diff[config_attr] = (starting_value, ending_value)
            ret["config"] = config_diff
        else:
            try:
                if starting_attr != ending_attr:
                    ret[attr] = (starting_attr, ending_attr)
            except Exception:
                import ipdb; ipdb.set_trace(context=9)
    return ret

def get_animated_mobjects(animation):
    ret = [animation.mobject]
    from manimlib.animation.transform import Transform
    if isinstance(animation, Transform) and animation.target_mobject is not None:
        ret.append(animation.target_mobject)
    return ret

def diff_list_contains_mobject_name(diff_list, mobject_name):
    return any(diff_contains_mobject_name(diff, mobject_name) for diff in diff_list)

def diff_contains_mobject_name(diff, mobject_name):
    if 'mobjects' in diff and mobject_name in diff['mobjects'].keys():
        return True
    if 'transformations' in diff and mobject_name in map(lambda t: t[1], diff['transformations']):
        return True
    return False

def mark_ids_required(mob_ids):
    for mob_id in mob_ids:
        if mob_id in initial_mobject_serializations:
            initial_mobject_serializations[mob_id]['required'] = True

"""
Updates the required status and required parent history of Mobjects in the
hierarchy of the Mobject that corresponds to mob_id. A Mobject is considered
required if a diff is applied to it while a Mobject in its hierarchy is added to
the Scene. If a Mobject is required then all Mobjects in its hierarchy are also
required.
"""
def check_required(mob_id):
    added_mobject_ids = []
    for mob in web_scene.mobjects:
        added_mobject_ids.extend(map(lambda mob: id(mob), mob.get_family()))

    required = False
    queue = [mob_id]
    while queue:
        parent_id = queue.pop()
        if parent_id in added_mobject_ids:
            required = True
            break
        parent_mobject = current_mobjects.get(parent_id, None)
        if parent_mobject:
            for child_id in map(lambda mob: id(mob), parent_mobject.submobjects):
                queue.append(child_id)

    family_ids = list(map(lambda mob: id(mob), current_mobjects[mob_id].get_family()))
    if required:
        mark_ids_required(family_ids)
        for parent_id in past_diffed_parents[mob_id]:
            mark_ids_required(past_hierarchy_when_diffed[parent_id][mob_id])
    else:
        for submob_id in family_ids:
            past_diffed_parents[submob_id].append(mob_id)
            past_hierarchy_when_diffed[mob_id][submob_id] = family_ids
