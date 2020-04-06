#!/usr/bin/env python
import types
import traceback
import manimlib.config
import manimlib.constants
from manimlib.extract_scene import (
    get_scene_classes_from_module,
    get_scenes_to_render,
)

def get_scene(code, scene_names):
    module = manimlib.config.get_module(code)
    config = {
        'scene_names': scene_names,
        'open_video_upon_completion' : True,
        'show_file_in_finder' : False,
        'quiet' : False,
        'ignore_waits' : True,
        'write_all' : False,
        'sound' : False,
        'media_dir' : None,
        'video_dir' : None,
        'video_output_dir' : None,
        'tex_dir' : None,
        'scene_kwargs' : {
            'camera_config' : {
               'pixel_height' : 480,
               'pixel_width' : 854,
               'frame_rate' : 15,
            },
            'file_writer_config' : {
               'write_to_movie' : True,
               'save_last_frame' : False,
               'save_pngs' : False,
               'save_as_gif' : False,
               'png_mode' : 'RGB',
               'movie_file_extension' : '.mp4',
               'file_name' : None,
               'input_file_path' : 'example_scenes.py'
            },
            'skip_animations' : False,
            'start_at_animation_number' : None,
            'end_at_animation_number' : None,
            'leave_progress_bars' : False,
        }
    }

    all_scene_classes = get_scene_classes_from_module(module)
    scene_classes_to_render = get_scenes_to_render(all_scene_classes, config)

    for SceneClass in scene_classes_to_render:
        try:
            return SceneClass(**config['scene_kwargs'])
        except Exception:
            print("\n\n")
            traceback.print_exc()
            print("\n\n")

def get_scene_choices(code):
    module = manimlib.config.get_module(code)
    scene_classes = get_scene_classes_from_module(module)
    scene_choices = list(map(lambda cls: cls.__name__, scene_classes))
    return scene_choices
