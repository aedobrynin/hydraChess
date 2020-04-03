from celery import Celery
import celery_config


def make_celery(app):
    """Sets up celery instance for work with flask"""

    celery = Celery(app.import_name)
    celery.config_from_object(celery_config)
    celery.conf.update(app.config)

    TaskBase = celery.Task

    class ContextTask(TaskBase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask
    return celery
