import kubernetes
import kubernetes.client
import threading

global_configs = {}


class global_logger:

    local = threading.local()

    def __init__(self, logger):
        self.logger = logger

    def __enter__(self):
        self.previous = getattr(global_logger.local, "current", None)
        global_logger.local.current = self.logger

    def __exit__(self, *args):
        global_logger.local.current = self.previous


def get_logger():
    return global_logger.local.current


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


def matches_target_namespace(name, resource, configs=None):
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
                labels = lookup(resource, "metadata.labels", {})
                for key, value in match_labels.items():
                    if labels.get(key) != value:
                        continue
                else:
                    yield secret

                continue

            yield secret


def matches_source_secret(name, namespace, configs=None):
    """Returns all configs which are candidates to be applied based on
    the specified secret being changed.

    """

    if configs is None:
        configs = global_configs.values()

    for config in configs:
        secrets = lookup(config, "spec.secrets", [])

        for secret in secrets:
            if secret["name"] == name and secret["namespace"] == namespace:
                yield config
                continue


def reconcile_namespace(name, resource):
    """Perform reconciliation of the specified namespace.

    """

    secrets = list(matches_target_namespace(name, resource))

    if secrets:
        update_secrets(name, secrets)


def reconcile_config(name, resource):
    """Perform reconciliation for the specified config.

    """

    core_api = kubernetes.client.CoreV1Api()
    namespaces = core_api.list_namespace()

    for namespace in namespaces.items:
        secrets = list(
            matches_target_namespace(namespace.metadata.name, namespace, [resource])
        )

        if secrets:
            update_secrets(namespace.metadata.name, secrets)


def reconcile_secret(name, resource, namespace):
    """Perform reconciliation for the specified secret.

    """

    configs = list(matches_source_secret(name, namespace))

    for config in configs:
        reconcile_config(config["metadata"]["name"], config)


def update_secret(name, secret):
    """Updates a single secret in the specified namespace.

    """

    core_api = kubernetes.client.CoreV1Api()

    # Read the source secret to be copied or to be used for update. If
    # it doesn't exist, we will fail for just this update. We don't
    # raise an exception as it will break any reconcilation loop being
    # applied at larger context.

    source_namespace = lookup(secret, "namespace")
    source_secret_name = lookup(secret, "name")

    target_namespace = name
    target_secret_name = lookup(secret, "newName", source_secret_name)

    try:
        source_secret = core_api.read_namespaced_secret(
            namespace=source_namespace, name=source_secret_name
        )
    except kubernetes.client.rest.ApiException as e:
        get_logger().warning(
            f"Secret {source_secret_name} in namespace {source_namespace} cannot be read."
        )
        return

    # Now check whether the target secret already exists in the target
    # namespace. If it doesn't exist we just need to copy it, apply any
    # labels and we are done. Fail outright if get any errors besides
    # not being able to find the resource as that indicates a bigger
    # problem.

    target_secret = None

    try:
        target_secret = core_api.read_namespaced_secret(
            namespace=target_namespace, name=target_secret_name
        )
    except kubernetes.client.rest.ApiException as e:
        if e.status != 404:
            raise

    if target_secret is None:
        secret_body = {
            "apiVersion": "v1",
            "kind": "Secret",
            "metadata": {"name": target_secret_name},
        }

        secret_labels = source_secret.metadata.labels or {}
        secret_labels.update(lookup(secret, "applyLabels", {}))

        secret_body["metadata"]["labels"] = secret_labels

        secret_body["type"] = source_secret.type
        secret_body["data"] = source_secret.data

        try:
            core_api.create_namespaced_secret(
                namespace=target_namespace, body=secret_body
            )
        except kubernetes.client.rest.ApiException as e:
            if e.status == 409:
                get_logger().warning(
                    f"Secret {target_secret_name} in namespace {target_namespace} already exists."
                )
                return
            raise

        get_logger().info(
            f"Copied secret {source_secret_name} from namespace {source_namespace} to target namespace {target_namespace} as {target_secret_name}."
        )

        return

    # If the secret already existed, we need to determine if the
    # original secret had changed and if it had, update the secret in
    # the namespace. We compare by looking at the labels, secret type
    # and data.

    apply_labels = lookup(secret, "applyLabels", {})

    source_labels = source_secret.metadata.labels or {}
    source_labels.update(apply_labels)

    target_labels = target_secret.metadata.labels or {}

    if (
        source_secret.type == target_secret.type
        and source_secret.data == target_secret.data
        and source_labels == target_labels
    ):
        return

    target_secret.type = source_secret.type
    target_secret.data = source_secret.data

    target_secret.metadata.labels = source_labels

    core_api.replace_namespaced_secret(
        namespace=target_namespace, name=target_secret_name, body=target_secret
    )

    get_logger().info(
        f"Updated secret {target_secret_name} in namespace {target_namespace} from secret {source_secret_name} in namespace {source_namespace}."
    )


def update_secrets(name, secrets):
    """Update the specified secrets in the namespace.

    """

    for secret in secrets:
        update_secret(name, secret)
