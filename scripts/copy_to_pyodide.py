#!/usr/bin/env python
import logging
import os
from pathlib import Path
import shutil
import subprocess as sp
import sys
import pty
import select

from manim import __version__ as manim_version
from rich.logging import RichHandler

# Configure logging.
logging.basicConfig(
    level="NOTSET", format="%(message)s", datefmt="[%X]", handlers=[RichHandler()]
)
log = logging.getLogger("rich")

# Compute global variables.
pyodide_path = sys.argv[1]
manim_package_directory = Path(pyodide_path) / "packages" / "manim"
manim_source_directory = manim_package_directory / "src"

META_YAML = f"""
package:
  name: manim
  version: {manim_version}
source:
  path: ./src
requirements:
  run:
    - numpy
test:
  imports:
  - manim
"""


def get_manim_directory():
    script_dir = os.path.dirname(os.path.realpath(__file__))
    return Path(script_dir).parent


def generate_setup_py():
    log.info("Generating setup.py...")
    os.chdir(get_manim_directory())
    sp.run(["poetry", "build"])
    sp.run(
        [
            "tar",
            "-xvf",
            f"dist/manim-{manim_version}.tar.gz",
            "--no-anchored",
            f"manim-{manim_version}/setup.py",
            "--strip-components=1",
        ]
    )


def copy_to_pyodide():
    log.info("Copying source into pyodide directory...")
    if os.path.isdir(manim_package_directory):
        shutil.rmtree(manim_package_directory)
    os.mkdir(manim_package_directory)
    shutil.copytree("../manim", manim_source_directory)


def write_meta_yaml():
    log.info("Writing meta.yaml...")
    with open(Path(manim_package_directory) / "meta.yaml", "w") as f:
        f.write(META_YAML)


if len(sys.argv) < 2:
    print(f"Usage: {sys.argv[0]} PATH_TO_PYODIDE")
    sys.exit(1)

generate_setup_py()
copy_to_pyodide()
write_meta_yaml()
