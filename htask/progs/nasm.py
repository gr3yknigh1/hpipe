from __future__ import annotations
from typing import Sequence

import sys


from htask import Context

__all__ = ("assemble",)


if sys.platform == "win32":
    # TODO: Check for bitness
    DEFAULT_OUTPUT_FORMAT = "win64"
    DEFAULT_DEBUG_FORMAT = "cv8"
elif sys.platform == "linux":
    # TODO: Check for bitness
    DEFAULT_OUTPUT_FORMAT = "elf64"
    DEFAULT_DEBUG_FORMAT = "dwarf"
else:
    # TODO: Make better exception
    raise Exception(f"Unsupported platform: {sys.platform!r}")


def assemble(
    c: Context,
    sources: Sequence[str],
    *,
    output: str,
    output_format=DEFAULT_OUTPUT_FORMAT,
    debug_format=DEFAULT_DEBUG_FORMAT,
):
    # TODO: Make more options and make NASM.EXE discovery like in cmake wrapper.
    # TODO: Make debug optional

    sources_formatted = " ".join(sources)

    return c.run(f"nasm -f {output_format} -g -F {debug_format} {sources_formatted} -o {output}")
    

