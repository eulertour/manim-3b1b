import js
import pyodide
from colour import Color

def get_mobject_style(mob):
    stroke_rgbas = mob.get_stroke_rgbas()
    fill_rgbas = mob.get_fill_rgbas()

    if len(stroke_rgbas) != 1:
        print("Multiple stroke rgbas are not supported, using the first one.")
    if len(fill_rgbas) != 1:
        print("Multiple fill rgbas are not supported, using the first one.")

    return {
        "strokeColor": Color(rgb=stroke_rgbas[0][:3]).hex_l,
        "strokeOpacity": stroke_rgbas[0][3],
        "fillColor": Color(rgb=fill_rgbas[0][:3]).hex_l,
        "fillOpacity": fill_rgbas[0][3],
        "strokeWidth": mob.get_stroke_width(),
    }

def tex_to_points(tex):
    return pyodide.as_nested_list(js.tex_to_points(tex))
