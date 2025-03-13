from hpipe import define_job, Job

@define_job()
def echo(j: Job):
    j.run("echo 'Hi from orthan pipeline!'")
