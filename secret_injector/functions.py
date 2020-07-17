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


def matches_source_secret(secret_name, secret_obj, rule):
    """Returns true if the rule matches against the name of the specified
    secret.

    """

    # Check for where name selector is provided and ensure that
    # the secret is in the list. If a list is supplied but it
    # isn't in the list, then we skip to the next one. If both a
    # name selector and label selector exist, the label selector
    # will be ignored.

    match_names = lookup(rule, "sourceSecrets.nameSelector.matchNames", [])

    if match_names:
        if secret_name in match_names:
            return True

        return False

    # Check for were label selector is provided and ensure that
    # all the labels to be matched exist on the target namespace.

    match_labels = lookup(rule, "sourceSecrets.labelSelector.matchLabels", {})

    if match_labels:
        labels = lookup(secret_obj, "metadata.labels", {})
        for key, value in match_labels.items():
            if labels.get(key) != value:
                return False
        else:
            return True

    return False


def matches_service_account(service_account_name, service_account_obj, rule):
    """Returns true if the rule matches against the name of the specified
    service account.

    """

    # Check for where name selector is provided and ensure that
    # the secret is in the list. If a list is supplied but it
    # isn't in the list, then we skip to the next one. If both a
    # name selector and label selector exist, the label selector
    # will be ignored.

    match_names = lookup(rule, "serviceAccounts.nameSelector.matchNames", [])

    if match_names:
        if service_account_name in match_names:
            return True

        return False

    # Check for were label selector is provided and ensure that
    # all the labels to be matched exist on the target namespace.

    match_labels = lookup(rule, "serviceAccounts.labelSelector.matchLabels", {})

    if match_labels:
        labels = lookup(service_account_obj, "metadata.labels", {})
        for key, value in match_labels.items():
            if labels.get(key) != value:
                return False
        else:
            return True

    return True


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

        for rule in rules:
            reconcile_namespace(namespace_item.name, rule)


def reconcile_secret(secret_name, namespace_name, secret_obj):
    """Perform reconciliation for the specified secret.

    """

    api = pykube.HTTPClient(pykube.KubeConfig.from_env())

    try:
        namespace_item = pykube.Namespace.objects(api).get(name=namespace_name)
    except pykube.exceptions.ObjectDoesNotExist as e:
        return

    rules = list(
        matches_target_namespace(namespace_name, namespace_item.obj)
    )

    for rule in rules:
        if matches_source_secret(secret_name, secret_obj, rule):
            service_account_query = pykube.ServiceAccount.objects(api).filter(
                namespace=namespace_name
            )

            for service_account_item in service_account_query:
                if matches_service_account(
                    service_account_item.name, service_account_item.obj, rule
                ):
                    inject_secret(
                        namespace_name, secret_name, service_account_item
                    )


def reconcile_namespace(namespace_name, rule):
    """Applies the injection rule for the specified namespace.

    """

    api = pykube.HTTPClient(pykube.KubeConfig.from_env())

    # Need to list the secrets in the namespace and see if any match
    # the rule. If they do, then we see if there is a service account
    # that matches the rule which the secret should be injected into.

    secrets_query = pykube.Secret.objects(api).filter(namespace=namespace_name)

    for secret_item in secrets_query:
        if matches_source_secret(secret_item.name, secret_item.obj, rule):
            service_account_query = pykube.ServiceAccount.objects(api).filter(
                namespace=namespace_name
            )

            for service_account_item in service_account_query:
                if matches_service_account(
                    service_account_item.name, service_account_item.obj, rule
                ):
                    inject_secret(
                        namespace_name, secret_item.name, service_account_item
                    )


def inject_secret(namespace_name, secret_name, service_account_item):
    """Inject the name of the secret into the service account as an image
    pull secret if it is necessary.

    """

    # First check if already in the service account, in which case
    # can bail out straight away.

    image_pull_secrets = service_account_item.obj.get("imagePullSecrets", [])

    if {"name": secret_name} in image_pull_secrets:
        return

    # Now need to update the existing service account to add in the
    # name of the secret.

    image_pull_secrets.append({"name": secret_name})

    service_account_item.obj["imagePullSecrets"] = image_pull_secrets

    try:
        service_account_item.update()

    except pykube.exceptions.KubernetesError as e:
        get_logger().warning(
            f"Service account {service_account_item.name} in namespace {namespace_name} couldn't be updated."
        )

    else:
        get_logger().info(
            f"Injected secret {secret_name} into service account {service_account_item.name} in namespace {namespace_name}."
        )
