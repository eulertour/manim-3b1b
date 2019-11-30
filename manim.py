#!/usr/bin/env python
from manimlib import get_scene
import pprint

def main():
    with open("example_scenes.py", "r") as f:
        code = f.read()
    scene = get_scene(code, ["WriteStuff"])
    scene.render()

    pp = pprint.PrettyPrinter(indent=2)
    pp.pprint(scene.scenes_before_animation)
    pp.pprint(scene.animation_list)
    pp.pprint(scene.initial_mobject_dict)

if __name__ == "__main__":
    main()
