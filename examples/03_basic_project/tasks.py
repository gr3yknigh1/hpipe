
from htask import Context, define_task

@define_task()
def build(c: Context, configuration="Debug"):
    _ = c, configuration
