from hpipe import Pipeline
from hpipe import Job

pipeline = Pipeline()
pipeline.define_stages("echo")


@pipeline.define_job(stage="echo")
def echo(job: Job):
    job.run("echo 'Hello hpipe!'")
