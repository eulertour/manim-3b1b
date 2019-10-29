def animation_to_json(play_args, play_kwargs):
    animation = play_args[0]
    return {
      "className": animation.__class__.__name__,
      "args": animation.get_args(),
      "durationSeconds": animation.run_time,
    }

def mobjects_in_scene(scene):
    return list(map(lambda mob: id(mob), scene.mobjects))

def mobject_to_json(mob):
    return {
        "className": mob.__class__.__name__,
        "params": mob.kwargs,
        "position": mob.get_center(),
        "style": get_mobject_style(mob),
    }

def get_mobject_style(mob):
    return {
        "strokeColor": mob.get_stroke_color().get_hex(),
        "fillColor": mob.get_fill_color().get_hex(),
        "strokeWidth": mob.get_stroke_width(),
    }
