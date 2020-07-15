import kubernetes
import kubernetes.client

global_configs = {}


def lookup(object, key, default=None):
    """Looks up a property within an object using a dotted path as key.
    If the property isn't found, then return the default value.

    """

    keys = key.split(".")
    value = default

    for key in keys:
        value = object.get(key)
        if value is None:
            return default

        object = value

    return value


def matches_target_namespace(name, namespace, configs=None):
    """Returns all secrets which are candidates to be copied into the
    namespace passed as argument.

    """

    if configs is None:
        configs = global_configs.values()

    for config in configs:
        secrets = lookup(config, "spec.secrets", [])

        for secret in secrets:
            # Check for where name selector is provided and ensure that
            # the namespace is in the list. If a list is supplied but it
            # isn't in the list, then we skip to the next one. If both a
            # name selector and label selector exist, the label selector
            # will be ignored.

            match_names = lookup(secret, "targetNamespaces.nameSelector.matchNames", [])
            if match_names:
                if name in match_names:
                    yield secret

                continue

            # Check for were label selector is provided and ensure that
            # all the labels to be matched exist on the target namespace.

            match_labels = lookup(
                secret, "targetNamespaces.labelSelector.matchLabels", {}
            )
            if match_labels:
                labels = lookup(namespace, "metadata.labels", {})
                for key, value in match_labels.items():
                    if labels.get(key) != value:
                        continue
                else:
                    yield secret

                continue

            yield secret


def reconcile_namespace(name, namespace):
    secrets = list(matches_target_namespace(name, namespace))

    if secrets:
        update_secrets(name, secrets)


def reconcile_config(name, config):
    core_api = kubernetes.client.CoreV1Api()
    namespaces = core_api.list_namespace()

    for namespace in namespaces.items:
        secrets = list(
            matches_target_namespace(namespace.metadata.name, namespace, [config])
        )

        if secrets:
            update_secrets(namespace.metadata.name, secrets)


def update_secrets(name, secrets):
    print(f'UDPATE SECRETS IN {name}:', secrets)
