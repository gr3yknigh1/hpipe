from __future__ import annotations
from typing import Sequence
from typing import Optional

import sys
import os.path


from htask import Context

__all__ = ("assemble",)


if sys.platform == "win32":
    # TODO: Check for bitness
    DEFAULT_OUTPUT_FORMAT = "win64"
    DEFAULT_DEBUG_FORMAT = "cv8"

    OBJECT_FILE_EXT = "obj"
elif sys.platform == "linux":
    # TODO: Check for bitness
    DEFAULT_OUTPUT_FORMAT = "elf64"
    DEFAULT_DEBUG_FORMAT = "dwarf"
    OBJECT_FILE_EXT = "o"
else:
    # TODO: Make better exception
    raise Exception(f"Unsupported platform: {sys.platform!r}")


def assemble(
    c: Context,
    sources: Sequence[str],
    *,
    output: Optional[str]=None,
    output_format=DEFAULT_OUTPUT_FORMAT,
    debug_format=DEFAULT_DEBUG_FORMAT,
):
    # TODO: Make more options and make NASM.EXE discovery like in cmake wrapper.
    # TODO: Make debug optional

    if len(sources) == 0:
        raise Exception("No sources was provided!") # TODO: Make error printing with htask API 

    file_name, file_ext = os.path.splitext(
        os.path.basename(sources[0])
    )

    if output is None:
        output = c.join(c.cwd(), f"{file_name}.{OBJECT_FILE_EXT}")
    elif os.path.isdir(output):
        output = c.join(output, f"{file_name}.{OBJECT_FILE_EXT}")

    sources_formatted = " ".join(sources)

    return c.run(f"nasm -f {output_format} -g -F {debug_format} {sources_formatted} -o {output}")
    

