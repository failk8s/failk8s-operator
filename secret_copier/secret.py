import kopf

from .functions import global_logger, reconcile_secret


@kopf.on.event("", "v1", "secrets")
def secret_event(type, event, logger, **_):
    obj = event["object"]
    namespace = obj["metadata"]["namespace"]
    name = obj["metadata"]["name"]

    # If secret already exists, indicated by type being None, the
    # secret is added or modified later, do a full reconcilation to
    # ensure whether secret is now a candidate to copying.

    with global_logger(logger):
        if type in (None, "ADDED", "MODIFIED"):
            reconcile_secret(name, namespace, obj)
