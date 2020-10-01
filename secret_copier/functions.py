import threading
import pykube

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


def lookup(obj, key, default=None):
    """Looks up a property within an object using a dotted path as key.
    If the property isn't found, then return the default value.

    """

    keys = key.split(".")
    value = default

    for key in keys:
        value = obj.get(key)
        if value is None:
            return default

        obj = value

    return value


def matches_target_namespace(namespace_name, namespace_obj, configs=None):
    """Returns all rules which match the namespace passed as argument.

    """

    if configs is None:
        configs = global_configs.values()

    for config_obj in configs:
        rules = lookup(config_obj, "spec.rules", [])

        for rule in rules:
            # Check for where name selector is provided and ensure that
            # the namespace is in the list. If a list is supplied but it
            # isn't in the list, then we skip to the next one. If both a
            # name selector and label selector exist, the label selector
            # will be ignored.

            match_names = lookup(rule, "targetNamespaces.nameSelector.matchNames", [])

            if match_names:
                if namespace_name in match_names:
                    yield rule

                continue

            # Check for where label selector is provided and ensure that
            # all the labels to be matched exist on the target namespace.

            match_labels = lookup(
                rule, "targetNamespaces.labelSelector.matchLabels", {}
            )

            if match_labels:
                namespace_labels = lookup(namespace_obj, "metadata.labels", {})
                for key, value in match_labels.items():
                    if namespace_labels.get(key) != value:
                        break
                else:
                    yield rule

            else:
                yield rule


def matches_source_secret(secret_name, secret_namespace, configs=None):
    """Returns all configs which match the sectet passed as argument.

    """

    if configs is None:
        configs = global_configs.values()

    for config_obj in configs:
        rules = lookup(config_obj, "spec.rules", [])

        for rule in rules:
            source_secret_name = lookup(rule, "sourceSecret.name")
            source_secret_namespace = lookup(rule, "sourceSecret.namespace")

            if (
                secret_name == source_secret_name
                and secret_namespace == source_secret_namespace
            ):
                yield config_obj
                continue


def reconcile_namespace(namespace_name, namespace_obj):
    """Perform reconciliation of the specified namespace.

    """

    rules = list(matches_target_namespace(namespace_name, namespace_obj))

    if rules:
        update_secrets(namespace_name, rules)


def reconcile_config(config_name, config_obj):
    """Perform reconciliation for the specified config.

    """

    api = pykube.HTTPClient(pykube.KubeConfig.from_env())

    namespace_query = pykube.Namespace.objects(api)

    for namespace_item in namespace_query:
        rules = list(
            matches_target_namespace(
                namespace_item.name, namespace_item.obj, [config_obj]
            )
        )

        if rules:
            update_secrets(namespace_item.name, rules)


def reconcile_secret(secret_name, secret_namespace, secret_obj):
    """Perform reconciliation for the specified secret.

    """

    configs = list(matches_source_secret(secret_name, secret_namespace))

    for config_obj in configs:
        reconcile_config(config_obj["metadata"]["name"], config_obj)


def update_secret(namespace_name, rule):
    """Updates a single secret in the specified namespace.

    """

    api = pykube.HTTPClient(pykube.KubeConfig.from_env())

    # Read the source secret to be copied or to be used for update. If
    # it doesn't exist, we will fail for just this update. We don't
    # raise an exception as it will break any reconcilation loop being
    # applied at larger context. Even if the target secret name is
    # different, don't copy the secret back to the same namespace.

    source_secret_name = lookup(rule, "sourceSecret.name")
    source_secret_namespace = lookup(rule, "sourceSecret.namespace")

    target_secret_name = lookup(rule, "targetSecret.name", source_secret_name)
    target_secret_namespace = namespace_name

    if source_secret_namespace == target_secret_namespace:
        return

    try:
        source_secret_item = (
            pykube.Secret.objects(api)
            .filter(namespace=source_secret_namespace)
            .get(name=source_secret_name)
        )

    except pykube.exceptions.KubernetesError as e:
        get_logger().warning(
            f"Secret {source_secret_name} in namespace {source_secret_namespace} cannot be read."
        )
        return

    # Now check whether the target secret already exists in the target
    # namespace. If it doesn't exist we just need to copy it, apply any
    # labels and we are done. Fail outright if get any errors besides
    # not being able to find the resource as that indicates a bigger
    # problem.

    target_secret_item = None

    try:
        target_secret_item = (
            pykube.Secret.objects(api)
            .filter(namespace=target_secret_namespace)
            .get(name=target_secret_name)
        )

    except pykube.exceptions.ObjectDoesNotExist:
        pass

    if target_secret_item is None:
        target_secret_obj = {
            "apiVersion": "v1",
            "kind": "Secret",
            "metadata": {
                "name": target_secret_name,
                "namespace": target_secret_namespace,
            },
        }

        #target_secret_labels = source_secret_item.labels
        #target_secret_labels.update(lookup(rule, "targetSecret.labels", {}))

        target_secret_labels = lookup(rule, "targetSecret.labels", {})

        target_secret_obj["metadata"]["labels"] = target_secret_labels

        target_secret_obj["type"] = source_secret_item.obj["type"]
        target_secret_obj["data"] = source_secret_item.obj["data"]

        try:
            pykube.Secret(api, target_secret_obj).create()

        except pykube.exceptions.HTTPError as e:
            if e.code == 409:
                get_logger().warning(
                    f"Secret {target_secret_name} in namespace {target_secret_namespace} already exists."
                )
                return
            raise

        get_logger().info(
            f"Copied secret {source_secret_name} from namespace {source_secret_namespace} to target namespace {target_secret_namespace} as {target_secret_name}."
        )

        return

    # If the secret already existed, we need to determine if the
    # original secret had changed and if it had, update the secret in
    # the namespace. We compare by looking at the labels, secret type
    # and data.

    labels = lookup(rule, "targetSecret.labels", {})

    source_secret_labels = source_secret_item.labels
    source_secret_labels.update(labels)

    target_secret_labels = target_secret_item.labels

    if (
        source_secret_item.obj["type"] == target_secret_item.obj["type"]
        and source_secret_item.obj["data"] == target_secret_item.obj["data"]
        and source_secret_labels == target_secret_labels
    ):
        return

    target_secret_item.obj["type"] = source_secret_item.obj["type"]
    target_secret_item.obj["data"] = source_secret_item.obj["data"]

    target_secret_item.obj["metadata"]["labels"] = source_secret_labels

    target_secret_item.update()

    get_logger().info(
        f"Updated secret {target_secret_name} in namespace {target_secret_namespace} from secret {source_secret_name} in namespace {source_secret_namespace}."
    )


def update_secrets(name, secrets):
    """Update the specified secrets in the namespace.

    """

    for secret in secrets:
        update_secret(name, secret)
