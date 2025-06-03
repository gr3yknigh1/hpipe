from typing import Any

from os import getcwd, getenv
from os.path import exists, join, dirname
import subprocess

from invoke import task, Context

project_folder = dirname(__file__)
dist_folder = join(project_folder, "dist")

sources = (
    join(project_folder, "hbuild", "__init__.py"),
    join(project_folder, "hbuild", "__main__.py"),
)

env_path = join(getcwd(), ".venv")
env_vars = [
    "PATH",
    "_OLD_VIRTUAL_PATH",
    "VIRTUAL_ENV",
    "VIRTUAL_ENV_PROMPT",
]


def extract_env_from_venv_activation_script(
    env_activation_script: str,
    environment_vars: list[str],
) -> dict[str, Any]:
    process = subprocess.Popen(
        [env_activation_script, "&&", "set"], stdout=subprocess.PIPE
    )
    output = process.stdout.read().decode("utf-8")

    # NOTE(gr3yknigh1): Ha-ha, nasty, but it is on purpose! [2025/02/03]
    env = {
        item[0].upper(): item[1]
        for item in (line.split("=") for line in output.splitlines())
        if len(item) == 2 and item[0].upper() in environment_vars
    }

    return env


@task
def configure(c: Context, dev=False, clean=False):
    with c.cd(getcwd()):
        activate_bat = join(env_path, "Scripts", "activate.bat")
        pip_path_exe = join(env_path, "Scripts", "pip.exe")

        if clean and exists(pip_path_exe):
            c.run(f"rmdir /S /Q {env_path}")

        if not exists(pip_path_exe) or clean:
            c.run(f"python -m venv {env_path}")

        env = extract_env_from_venv_activation_script(activate_bat, env_vars)
        c.run("python -m pip install --upgrade pip", env=env)

        if dev:
            c.run(f"python -m pip install --editable {c.cwd}", env=env)
            c.run(f"python -m pip install --editable {c.cwd}[dev]", env=env)
            c.run(f"python -m pip install --editable {c.cwd}[types]", env=env)
        else:
            c.run(f"python -m pip install {c.cwd}", env=env)

@task()
def format(c: Context) -> None:

    activate_bat = join(env_path, "Scripts", "activate.bat")
    env = extract_env_from_venv_activation_script(activate_bat, env_vars)

    c.run(f"ruff format {' '.join(sources)}", env=env)

@task()
def lint(c: Context) -> None:

    activate_bat = join(env_path, "Scripts", "activate.bat")
    env = extract_env_from_venv_activation_script(activate_bat, env_vars)

    c.run(f"mypy {' '.join(sources)}", env=env)
    c.run(f"ruff check --respect-gitignore {' '.join(sources)}", env=env)
    c.run(f"ruff format --respect-gitignore --check --diff {' '.join(sources)}", env=env)
