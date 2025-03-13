
from hpipe import define_job, Job


@define_job()
def _build(j: Job):
    j.run("echo I: Building...")
