#!/usr/bin/env python
import sys
import re

# TODO: Handle multi-line __init__() functions.
# Groups are required arguments followed by keyword arguments
INIT_REGEX = "(\\s*)def __init__\\(self(, [^=]+)*(, .+)*, \\*\\*kwargs\\)"

if len(sys.argv) < 2:
    print("Specify files to update")

prog = re.compile(INIT_REGEX)
for path in sys.argv[1:]:
    newlines = ["from manimlib.web.utils import serialize_args, serialize_config\n"]
    with open(path, "r") as f:
        lines = f.readlines()
        for line in lines:
            result = prog.match(line)
            newlines.append(line)
            args = []
            kwargs = []
            if result:
                # Save args
                spacing = result.group(1) + "    "
                newlines.append(f"{spacing}if not hasattr(self, \"args\"):\n")
                if result.group(2):
                    args = result.group(2).split(", ")[1:]
                newline = f"{spacing}    self.args = "
                if len(args) > 0 and args[0].startswith("*"):
                    assert(len(args) == 1)
                    newline += f"serialize_args({args[0][1:]})\n"
                else:
                    newline += f"serialize_args([{', '.join(list(args))}])\n"
                newlines.append(newline)

                # Save kwargs
                newlines.append(f"{spacing}if not hasattr(self, \"config\"):\n")
                if result.group(3):
                    kwargs = result.group(3).split(", ")[1:]
                    kwargs = map(lambda keyval: keyval.split("=")[0], kwargs)
                newline = spacing + "    self.config = serialize_config({\n"
                for kwarg in kwargs:
                    newline += spacing + "        " + f"'{kwarg}': {kwarg},\n"
                newline += spacing + "        " + f"**kwargs,\n"
                newline += spacing + "    })\n"
                newlines.append(newline)
    # print("".join(newlines))
    with open(path, "w") as f:
        f.writelines(newlines)
