import numpy as np

def array_to_hex_color(arr):
    return "#" + "".join(map(
        lambda x: format(x, '02x'),
        np.around(arr * 255).astype(int),
    ))

def get_mobject_style(mob):
    stroke_rgbas = mob.get_stroke_rgbas()
    fill_rgbas = mob.get_fill_rgbas()
    return {
        "strokeColor": array_to_hex_color(stroke_rgbas[0][:3]),
        "strokeOpacity": stroke_rgbas[0][3],
        "fillColor": array_to_hex_color(fill_rgbas[0][:3]),
        "fillOpacity": fill_rgbas[0][3],
        "strokeWidth": mob.get_stroke_width(),
    }
