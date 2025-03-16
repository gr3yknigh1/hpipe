
from hpipe import define_job, Job

@define_job()
def build(j: Job):

    j.cwd

    j.run("echo I: Building...")
