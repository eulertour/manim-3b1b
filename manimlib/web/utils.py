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
# Maps a given Mobject ID to a human-readable name for that Mobject.
mobject_ids_to_names = {}
# List of transformations applied to Mobjects in the order they are applied.
transformation_list = []
next_unserialized_transformation_index = 0

def get_unserialized_transformations():
    global next_unserialized_transformation_index
    ret = transformation_list[next_unserialized_transformation_index:]
    next_unserialized_transformation_index = len(transformation_list)
    return ret

def register_transformation(mob_id, *transformation):
    transformation_list.append((
        len(transformation_list),
        mob_id,
        *transformation,
    ))

def register_mobject(mob):
    mob_id = id(mob)
    if mob_id not in current_mobjects:
        current_mobjects[mob_id] = mob
        name_mobject(mob_id, mob.__class__.__name__)

    initial_mobject_serializations[mob_id] = serialize_mobject(mob)
    prior_mobject_serializations[mob_id] = \
            copy.deepcopy(initial_mobject_serializations[mob_id])


def name_mobject(mob_id, class_name):
    mob_name = f"{class_name}{mobject_class_counts[class_name]}"
    mobject_ids_to_names[mob_id] = mob_name
    mobject_class_counts[class_name] += 1


def rename_initial_mobject_serializations():
    new_mobject_dict = {}
    for mob_id in initial_mobject_serializations:
        new_serialization = initial_mobject_serializations[mob_id]
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
                    new_diff["mobjects"][mobject_ids_to_names[mob_id]] = rename_diff(diff["mobjects"][mob_id])
            elif attr == "transformations":
                # This is the transformation list. Transformations have the form
                # (index, mob_id, *params)
                new_transformations = []
                for transformation in diff[attr]:
                    if transformation[1] in mobject_ids_to_names:
                        new_transformations.append((
                            transformation[0],
                            mobject_ids_to_names[transformation[1]],
                            *transformation[2:],
                        ))
                    else:
                        # Serialized the transformation of a Mobject that wasn't
                        # created by the user (e.g. from ApplyPointwiseFunction
                        # where a target Mobject is created and transformed
                        # internally).
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
    new_info = []
    for info in animation_info_list:
        animation_class = info["className"]
        args = info["args"]
        config = info["config"]
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
        new_info.append({
            "className": animation_class,
            "args": new_args,
            "config": new_config,
        })
    return new_info


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

def animation_to_json(play_args, play_kwargs):
    animation = play_args[0]
    if animation.__class__.__name__ == "ApplyPointwiseFunction":
        args = animation.get_args()
        return {
          "className": animation.__class__.__name__,
          "args": list(map(lambda mob: id(mob), args[1])),
          "durationSeconds": animation.run_time,
          "func": pointwise_function_wrapper(args[0]),
        }
    else:
        return {
          "className": animation.__class__.__name__,
          "args": list(map(lambda mob: id(mob), animation.get_args())),
          "durationSeconds": animation.run_time,
        }

def wait_to_json(duration, stop_condition):
    return {
        "className": "Wait",
        "args": [],
        "durationSeconds": duration,
        "stopCondition": stop_condition,
        "description": "Hold a still frame",
        "argDescriptions": [],
    }

def scene_mobjects_to_json(mobjects):
    return list(map(lambda mob: {
        "name": id(mob),
        "submobjects": scene_mobjects_to_json(mob.submobjects),
    }, mobjects))

def mobject_to_json(mob):
    from manimlib.mobject.mobject import Group, Mobject
    from manimlib.mobject.types.vectorized_mobject import VMobject, VGroup
    if isinstance(mob, VMobject):
        ret = {
            "className": mob.__class__.__name__,
            "params": mob.kwargs,
            "position": mob.get_center(),
            "style": get_mobject_style(mob),
            "submobjects": [id(mob) for mob in mob.submobjects],
            "transformations": mob.transformations,
        }
        return ret
    elif type(mob) in [Group, Mobject, VGroup, VMobject]:
        return {
            "className": mob.__class__.__name__,
            "submobjects": [id(mob) for mob in mob.submobjects],
            "params": mob.kwargs,
            "transformations": mob.transformations,
        }
    else:
        print(mob)
        raise NotImplementedError("Mobject not available in javascript")


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

def serialize_animation(animation):
    return {
        "className": animation.__class__.__name__,
        "args": animation.args,
        "config": animation.config,
    }

def serialize_wait(duration, stop_condition):
    return {
        "className": "Wait",
        "args": [],
        "config": {
            "duration": duration,
            "stop_condition": stop_condition,
        },
    }

CLASSES_WHOSE_CHILDREN_ARE_NOT_SERIALIZED = ["TexMobject", "TextMobject", "SingleStringTexMobject"]

def serialize_mobject(mob, added=False):
    from manimlib.mobject.mobject import Group, Mobject
    from manimlib.mobject.types.vectorized_mobject import VMobject, VGroup
    class_name = mob.__class__.__name__
    ret = {
        "className": class_name,
        "args": copy.deepcopy(mob.args),
        "config": copy.deepcopy(mob.config),
        "added": added,
    }
    if class_name not in CLASSES_WHOSE_CHILDREN_ARE_NOT_SERIALIZED:
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
        elif attr == "position":
            if not np.array_equal(starting_attr, ending_attr):
                ret[attr] = (starting_attr, ending_attr)
        elif attr == "transformations":
            if not transform_lists_equal(starting_attr, ending_attr):
                ret[attr] = (starting_attr, ending_attr)
        else:
            if starting_attr != ending_attr:
                ret[attr] = (starting_attr, ending_attr)
    return ret

def get_animated_mobjects(animation):
    ret = [animation.mobject]
    from manimlib.animation.transform import Transform
    if isinstance(animation, Transform) and animation.target_mobject is not None:
        ret.append(animation.target_mobject)
    return ret
