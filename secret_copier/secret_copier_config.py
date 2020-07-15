import kopf

from .functions import global_configs, reconcile_config


@kopf.on.create("failk8s.dev", "v1alpha1", "secretcopierconfigs", id="failk8s")
def create(name, body, logger, **_):
    global_configs[name] = body

    reconcile_config(name, body)


@kopf.on.resume("failk8s.dev", "v1alpha1", "secretcopierconfigs", id="failk8s")
def resume(name, body, logger, **_):
    global_configs[name] = body

    reconcile_config(name, body)


@kopf.on.update("failk8s.dev", "v1alpha1", "secretcopierconfigs", id="failk8s")
def update(name, body, logger, **_):
    global_configs[name] = body


@kopf.on.delete(
    "failk8s.dev", "v1alpha1", "secretcopierconfigs", id="failk8s", optional=True
)
def delete(name, body, logger, **_):
    try:
        del global_configs[name]
    except KeyError:
        pass
