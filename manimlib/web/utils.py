from manimlib.mobject.mobject import Group, Mobject
from manimlib.mobject.types.vectorized_mobject import VMobject

def animation_to_json(play_args, play_kwargs):
    animation = play_args[0]
    return {
      "className": animation.__class__.__name__,
      "args": list(map(lambda mob: id(mob), animation.get_args())),
      "durationSeconds": animation.run_time,
    }

def mobjects_in_scene(scene):
    return list(map(lambda mob: id(mob), scene.mobjects))

def mobject_to_json(mob):
    if isinstance(mob, VMobject):
        return {
            "className": mob.__class__.__name__,
            "params": mob.kwargs,
            "position": mob.get_center(),
            "style": get_mobject_style(mob),
            "submobjects": [id(mob) for mob in mob.submobjects],
        }
    elif type(mob) in [Group, Mobject]:
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
