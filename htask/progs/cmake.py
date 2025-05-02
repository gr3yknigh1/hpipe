from __future__ import annotations
from typing import Optional
from typing import Mapping

from os.path import join, exists
import os
import os.path
import shutil


from htask import Context


__all__ = ("configure",)


def is_file_executable(file_path: str) -> bool:
    return (
        os.path.exists 
        and os.path.isfile(file_path) 
        and os.access(file_path, os.X_OK)
    )


def configure(
    c: Context, 
    *,
    source_folder: Optional[str]=None,
    build_folder: Optional[str]=None,
    cmake_executable: Optional[str]=None,
    generator: Optional[str]=None,
    variables: Optional[Mapping[str, Any]]=None,
) -> None:

    if cmake_executable is None:
        cmake_executable = shutil.which("cmake")
        if cmake_executable is None:
            raise Exception("Failed to find cmake executable in the PATH.") # TODO(gr3yknigh1): Make custom exception [2025/05/02] #error_handling
        assert is_file_executable(cmake_executable)

    source_folder = source_folder if source_folder is not None else os.getcwd()
    build_folder = build_folder if build_folder is not None else join(source_folder, "build")
    variables = variables if variables is not None else {}

    command = f"{c.quote(cmake_executable)} -S {source_folder} -B {build_folder}"

    if generator is not None:
        command += f" -G {c.quote(generator)}"

    for key, value in variables.items():

        # Formatting for booleans
        if isinstance(value, bool):
            value = "ON" if value else "FALSE"

        command += f" -D {key}={str(value)}"

    c.run(command)

def build(
    c: Context,
    *,
    configuration_name="Debug",
    source_folder: Optional[str]=None,
    build_folder: Optional[str]=None,
    cmake_executable: Optional[str]=None
) -> None:

    if cmake_executable is None:
        cmake_executable = shutil.which("cmake")
        if cmake_executable is None:
            raise Exception("Failed to find cmake executable in the PATH.") # TODO(gr3yknigh1): Make custom exception [2025/05/02] #error_handling
        assert is_file_executable(cmake_executable)

    source_folder = source_folder if source_folder is not None else os.getcwd()
    build_folder = build_folder if build_folder is not None else join(source_folder, "build")

    command = f"{c.quote(cmake_executable)} --build {build_folder} --config {configuration_name}"
    c.run(command)

