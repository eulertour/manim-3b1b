#!/usr/bin/env python
import manimlib.config
import manimlib.constants
import manimlib.extract_scene


def main():
    args = manimlib.config.parse_cli()
    config = manimlib.config.get_configuration(args)
    manimlib.constants.initialize_directories(config)

    if config["use_javascript_svg_interpretation"]:
        manimlib.constants.USE_JAVASCRIPT_SVG_INTERPRETATION = True

    manimlib.extract_scene.main(config)
