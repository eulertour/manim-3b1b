from manimlib.mobject.mobject import Group, Mobject
from manimlib.mobject.types.vectorized_mobject import VMobject, VGroup
import sys
if sys.platform == "emscripten":
    import js
else:
    from manimlib.web.web_mock import tex2svg

def animation_to_json(play_args, play_kwargs):
    animation = play_args[0]
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
        }
        return ret
    elif type(mob) in [Group, Mobject, VGroup, VMobject]:
        return {
            "className": mob.__class__.__name__,
            "submobjects": [id(mob) for mob in mob.submobjects],
            "params": mob.kwargs,
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

def tex_to_svg_string(tex):
    if sys.platform == "emscripten":
        return js.MathJax.tex2svg(tex).innerHTML
    else:
        print("searching cache for " + tex)
        return tex2svg[tex]
