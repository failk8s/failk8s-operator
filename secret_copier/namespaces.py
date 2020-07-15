import kopf

from .functions import reconcile_namespace


@kopf.on.event("", "v1", "namespaces")
def my_handler(type, event, **_):
    resource = event["object"]
    name = resource["metadata"]["name"]

    # If namespace already exists, indicated by type being None, or the
    # namespace is added later, do a full reconcilation to ensure that
    # all the required secrets have been copied into the namespace.

    if type in (None, "ADDED"):
        reconcile_namespace(name, resource)
