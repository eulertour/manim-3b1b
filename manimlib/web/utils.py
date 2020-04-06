import sys
if sys.platform == "emscripten":
    import js
    import pyodide
else:
    from manimlib.web.web_mock import tex2points

def get_mobject_style(mob):
    return {
        "strokeColor": str(mob.get_stroke_color()),
        "strokeOpacity": mob.get_stroke_opacity(),
        "fillColor": str(mob.get_fill_color()),
        "fillOpacity": mob.get_fill_opacity(),
        "strokeWidth": mob.get_stroke_width(),
    }

def tex_to_points(tex):
    if sys.platform == "emscripten":
        return pyodide.as_nested_list(js.texToPoints(tex))
    else:
        print("searching cache for " + tex)
        return tex2points(tex)
