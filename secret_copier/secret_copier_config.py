import kopf

from .functions import global_logger, global_configs, reconcile_config


@kopf.on.create("failk8s.dev", "v1alpha1", "secretcopierconfigs")
def config_create(name, body, logger, **_):
    global_configs[name] = body

    with global_logger(logger):
        reconcile_config(name, body)

@kopf.on.resume("failk8s.dev", "v1alpha1", "secretcopierconfigs")
def config_resume(name, body, logger, **_):
    global_configs[name] = body

    with global_logger(logger):
        reconcile_config(name, body)


@kopf.on.update("failk8s.dev", "v1alpha1", "secretcopierconfigs")
def config_update(name, body, logger, **_):
    global_configs[name] = body

    with global_logger(logger):
        reconcile_config(name, body)

@kopf.on.delete("failk8s.dev", "v1alpha1", "secretcopierconfigs")
def config_delete(name, body, **_):
    try:
        del global_configs[name]
    except KeyError:
        pass