from manimlib.mobject.mobject import Group, Mobject
from manimlib.mobject.types.vectorized_mobject import VMobject, VGroup
import sys
if sys.platform == "emscripten":
    import js
    import pyodide
else:
    from manimlib.web.web_mock import tex2points

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
