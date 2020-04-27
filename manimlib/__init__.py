#!/usr/bin/env python
import os
import manimlib.config
import manimlib.constants
import manimlib.extract_scene


def main():
    args = manimlib.config.parse_cli()
    config = manimlib.config.get_configuration(args)

    if config["use_javascript_svg_interpretation"]:
        manimlib.constants.USE_JAVASCRIPT_SVG_INTERPRETATION = True
    if config["print_frames_only"]:
        manimlib.constants.PRINT_FRAMES_ONLY = True
    if config["change_directory"]:
        os.chdir(config["change_directory"])

    manimlib.constants.initialize_directories(config)
    manimlib.extract_scene.main(config)
