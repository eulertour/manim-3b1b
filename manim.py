#!/usr/bin/env python
from manimlib import get_scene

def main():
    with open("example_scenes.py", "r") as f:
        code = f.read()
    scene = get_scene(code, ["SquareToCircle"])
    scene.render()
    print(scene.scene_list)
    print(scene.render_list)
    print(scene.mobject_dict)

if __name__ == "__main__":
    main()
