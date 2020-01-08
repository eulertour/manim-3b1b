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

CLASSES_WHOSE_CHILDREN_ARE_NOT_SERIALIZED = ["TexMobject", "TextMobject"]

def serialize_mobject(mob, added=False):
    from manimlib.mobject.mobject import Group, Mobject
    from manimlib.mobject.types.vectorized_mobject import VMobject, VGroup
    class_name = mob.__class__.__name__
    ret = {
        "className": class_name,
        "args": copy.deepcopy(mob.args),
        "config": copy.deepcopy(mob.config),
        "transformations": copy.deepcopy(mob.transformations),
        "added": added,
    }
    if class_name not in CLASSES_WHOSE_CHILDREN_ARE_NOT_SERIALIZED:
        ret["submobjects"] = [id(mob) for mob in mob.submobjects]
    if isinstance(mob, VMobject):
        ret["position"] = mob.get_center()
        ret["style"] = get_mobject_style(mob)
    return ret

# ('rotate', angle, axis)
def rotate_transforms_equal(rotate1, rotate2):
    assert(rotate1[0] == 'rotate')
    assert(rotate1[0] == rotate2[0])
    if rotate1[1] != rotate2[1]:
        return False
    if not np.array_equal(rotate1[2], rotate2[2]):
        return False
    return True

def transforms_equal(transform1, transform2):
    command1, command2 = transform1[0], transform2[0]
    if command1 != command2:
        return False
    if command1 == "rotate":
        return rotate_transforms_equal(transform1, transform2)
    else:
        print(f"Unknown transformation {command1}")

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

def get_submobjects_for_serialization(mob):
    Q = collections.deque()
    Q.append(mob)
    ret = []
    while Q:
        parent = Q.pop()
        ret.append(parent)
        if parent.__class__.__name__ not in CLASSES_WHOSE_CHILDREN_ARE_NOT_SERIALIZED:
            for child in parent.submobjects:
                Q.append(child)
    return list(ret)

def get_mobject_hierarchies_from_mobject_list(mobs):
    recursive_mobjects_in_scene_map = map(lambda mob: get_submobjects_for_serialization(mob), mobs)
    recursive_mobjects_in_scene = it.chain(*[list(m) for m in recursive_mobjects_in_scene_map])
    return recursive_mobjects_in_scene

def get_mobject_hierarchies_from_scene(scene):
    return get_mobject_hierarchies_from_mobject_list(scene.mobjects)


def get_animated_mobjects(animation):
    ret = [animation.mobject]
    from manimlib.animation.transform import Transform
    if isinstance(animation, Transform) and animation.target_mobject is not None:
        ret.append(animation.target_mobject)
    return ret
