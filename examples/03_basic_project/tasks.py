
from htask import Context, define_task, load_env, save_env
from htask.progs import msvc


def _output_dir(c: Context, configuration="Debug"):
    return c.join(c.root, "build", configuration)


@define_task()
def build(c: Context, configuration="Debug", reconfigure=False):
    _ = c, configuration

    c.mkdir(_output_dir(c, configuration))
    cached_env = c.join(_output_dir(c, configuration), "vc_build.env")
    
    if not reconfigure and c.exists(cached_env):
        vc_env = load_env(cached_env)
    else:
        vc_env = msvc.extract_env_from_vcvars(c, arch="x64")
        save_env(cached_env, vc_env)

    msvc.compile(c, ["main.c"], output="basic.exe", env=vc_env)
