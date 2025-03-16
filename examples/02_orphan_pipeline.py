from hpipe import define_job, Context

@define_job()
def echo(c: Context):
    c.run("echo 'Hi from orthan pipeline!'")
