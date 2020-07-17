import kopf

from .functions import global_logger, reconcile_secret


@kopf.on.event("", "v1", "secrets")
def injector_secret_event(type, event, logger, **_):
    obj = event["object"]
    namespace = obj["metadata"]["namespace"]
    name = obj["metadata"]["name"]

    # If secret already exists, indicated by type being None, the
    # secret is added or modified later, do a full reconcilation to
    # ensure that if now match will inject the secret.

    with global_logger(logger):
        if type in (None, "ADDED", "MODIFIED"):
            reconcile_secret(name, namespace, obj)
