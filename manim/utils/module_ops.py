from .. import constants, logger, config
import importlib.util
import inspect
import os
from pathlib import Path
import sys
import types
import re

if sys.platform != "emscripten":
    from .. import console


def scene_class_from_code_and_name(code, scene_name):
    module = types.ModuleType("input_scenes")
    exec(code, module.__dict__)
    all_scene_classes = get_scene_classes_from_module(module)
    scene_classes_to_render = get_scenes_to_render(all_scene_classes, [scene_name])

    assert len(scene_classes_to_render) == 1
    return scene_classes_to_render[0]


def get_module_from_code():
    logger.info(
        "Enter the animation's code & end with an EOF (CTRL+D on Linux/Unix, CTRL+Z on Windows):"
    )
    code = sys.stdin.read()
    if not code.startswith("from manim import"):
        logger.warn(
            "Didn't find an import statement for Manim. Importing automatically..."
        )
        code = "from manim import *\n" + code
    logger.info("Rendering animation from typed code...")
    module = types.ModuleType("input_scenes")
    try:
        exec(code, module.__dict__)
        return module
    except Exception as e:
        logger.error(f"Failed to render scene: {str(e)}")
        sys.exit(2)


def get_module_from_file(file_name: Path):
    if Path(file_name).exists():
        ext = file_name.suffix
        if ext != ".py":
            raise ValueError(f"{file_name} is not a valid Manim python script.")
        module_name = ext.replace(os.sep, ".").split(".")[-1]
        spec = importlib.util.spec_from_file_location(module_name, file_name)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        sys.path.insert(0, str(file_name.parent.absolute()))
        spec.loader.exec_module(module)
        return module
    else:
        raise FileNotFoundError(f"{file_name} not found")


def get_scene_classes_from_module(module):
    from ..scene.scene import Scene

    def is_child_scene(obj, module):
        return (
            inspect.isclass(obj)
            and issubclass(obj, Scene)
            and obj != Scene
            and obj.__module__.startswith(module.__name__)
        )

    return [
        member[1]
        for member in inspect.getmembers(module, lambda x: is_child_scene(x, module))
    ]


def get_scenes_to_render(scene_classes, chosen_scene_names):
    if not scene_classes:
        logger.error(constants.NO_SCENE_MESSAGE)
        return []
    if config["write_all"]:
        return scene_classes
    result = []
    for scene_name in chosen_scene_names:
        found = False
        for scene_class in scene_classes:
            if scene_class.__name__ == scene_name:
                result.append(scene_class)
                found = True
                break
        if not found and (scene_name != ""):
            logger.error(constants.SCENE_NOT_FOUND_MESSAGE.format(scene_name))
    if result:
        return result
    return (
        [scene_classes[0]]
        if len(scene_classes) == 1
        else prompt_user_for_choice(scene_classes)
    )


def prompt_user_for_choice(scene_classes):
    num_to_class = {}
    for count, scene_class in enumerate(scene_classes):
        count += 1  # start with 1 instead of 0
        name = scene_class.__name__
        console.print(f"{count}: {name}", style="logging.level.info")
        num_to_class[count] = scene_class
    try:
        user_input = console.input(
            f"[log.message] {constants.CHOOSE_NUMBER_MESSAGE} [/log.message]"
        )
        return [
            num_to_class[int(num_str)]
            for num_str in re.split(r"\s*,\s*", user_input.strip())
        ]
    except KeyError:
        logger.error(constants.INVALID_NUMBER_MESSAGE)
        sys.exit(2)
    except EOFError:
        sys.exit(1)


def get_scene_classes(file_path, chosen_scene_names, require_single_scene=False):
    if str(file_path.name) == "-":
        module = get_module_from_code()
    else:
        module = get_module_from_file(file_path)
    all_scene_classes = get_scene_classes_from_module(module)
    scene_classes_to_render = get_scenes_to_render(
        all_scene_classes, chosen_scene_names
    )
    if require_single_scene:
        assert len(scene_classes_to_render) == 1
        return scene_classes_to_render[0]
    return scene_classes_to_render
