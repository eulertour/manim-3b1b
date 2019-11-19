#!/usr/bin/env python
from manimlib import get_scene
import pprint

def main():
    with open("example_scenes.py", "r") as f:
        code = f.read()
    scene = get_scene(code, ["GroupExample"])
    scene.render()

if __name__ == "__main__":
    main()
