import js
import pyodide

def get_mobject_style(mob):
    return {
        "strokeColor": str(mob.get_stroke_color()),
        "strokeOpacity": mob.get_stroke_opacity(),
        "fillColor": str(mob.get_fill_color()),
        "fillOpacity": mob.get_fill_opacity(),
        "strokeWidth": mob.get_stroke_width(),
    }

def tex_to_points(tex):
    return pyodide.as_nested_list(js.tex_to_points(tex))
