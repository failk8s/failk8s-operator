import kopf

from .functions import global_logger, reconcile_namespace


@kopf.on.event("", "v1", "namespaces")
def namespace_event(type, event, logger, **_):
    resource = event["object"]
    name = resource["metadata"]["name"]

    # If namespace already exists, indicated by type being None, or the
    # namespace is added or modified later, do a full reconcilation to
    # ensure that all the required secrets have been copied into the
    # namespace.

    with global_logger(logger):
        if type in (None, "ADDED", "MODIFIED"):
            reconcile_namespace(name, resource)
