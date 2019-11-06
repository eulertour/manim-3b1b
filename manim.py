#!/usr/bin/env python
from manimlib import get_scene
import pprint

def main():
    with open("example_scenes.py", "r") as f:
        code = f.read()
    scene = get_scene(code, ["GroupExample"])
    scene.render()

    pp = pprint.PrettyPrinter(indent=2)
    print(f"scene.scene_list = {pp.pformat(scene.scene_list)}\n")
    print(f"scene.render_list = {pp.pformat(scene.render_list)}\n")
    print(f"scene.mobject_dict = {pp.pformat(scene.mobject_dict)}\n")

if __name__ == "__main__":
    main()
