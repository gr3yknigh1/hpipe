from __future__ import annotations
from typing import Any
from typing import Dict
from typing import Optional
from typing import List

from os.path import exists
import subprocess

#
# VS utilities
#

DEFAULT_VC_BOOSTRAP_VARS = ["INCLUDE", "LIB", "LIBPATH", "PATH"]

def parse_env_file(file: str) -> dict[str, Any]:
    with open(file, mode="r") as f:
        s = f.read()

        env = {
            item[0] : item[1]
            for item in (
                l.split("=") for l in s.splitlines()
            ) if len(item) == 2
        }
    return env

def store_env_to_file(file: str, env: dict[str, Any]) -> None:
    with open(file, mode="w") as f:
        for k, v in env.items():
            f.write(f"{k}={v}\n")

def find_vc_bootstrap_script() -> str | None:
    #
    # Detect vcvarsall for x64 build...
    #
    
    default_vc2022_bootstrap = r"C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvarsall.bat"
    default_vc2019_bootstrap = r"C:\Program Files (x86)\Microsoft Visual Studio\2019\Preview\VC\Auxiliary\Build\vcvarsall.bat"

    if exists(default_vc2022_bootstrap):
        return default_vc2022_bootstrap

    if exists(default_vc2019_bootstrap):
        return default_vc2019_bootstrap

    return None

def extract_environment_from_bootstrap_script(arch="x64", bootstrap_script: str | None = None, environment_vars: list[str] | None=None) -> dict[str, Any]:
    if bootstrap_script is None:
        bootstrap_script = find_vc_bootstrap_script()

        if bootstrap_script is None:
            return {}

    if environment_vars is None:
        environment_vars = DEFAULT_VC_BOOSTRAP_VARS

    process = subprocess.Popen([bootstrap_script, arch, "&&", "set"], stdout=subprocess.PIPE)
    output = process.stdout.read().decode("utf-8")

    # NOTE(gr3yknigh1): Ha-ha, nasty, but it is on purpose! [2025/02/03]
    env = {
        item[0].upper() : item[1]
        for item in (
            l.split("=") for l in output.splitlines()
        ) if len(item) == 2 and item[0].upper() in environment_vars
    }

    return env
