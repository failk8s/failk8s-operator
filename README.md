Operator to support failk8s
===========================

This operator handles the copying of secrets between namespaces and the injection of image pull secrets into service accounts.

Note that the operator does not delete secrets previously copied if the
original secret is deleted, or if rules change such that it wouldn't have
been created in the first place. The name of a secret is also not removed
from the list of image pull secrets in a service account if the secret is
removed or rules change meaning it would no longer have been added.

To setup copying of secrets a custom resource exists called
``SecretCopierConfig``. You can create more than one of this type of
resource.

First example below will copy the secret from the specified namespace
into all other namespaces. It will not attempt to copy the secret into
the namespace it originated from.

```
apiVersion: failk8s.dev/v1alpha1
kind: SecretCopierConfig
metadata:
  name: registry-credentials
spec:
  rules:
  - sourceSecret:
      name: registry-credentials
      namespace: registry
```

To change the name of the secret when copied to the target namespace, set
``targetSecret.name``. Still will not copy it to the same namespace, even
though the name is different.

```
apiVersion: failk8s.dev/v1alpha1
kind: SecretCopierConfig
metadata:
  name: registry-credentials
spec:
  rules:
  - sourceSecret
      name: registry-credentials
      namespace: registry
    targetSecret:
      name: faik8s-registry-credentials
```

To specify labels that should be applied to the secret when copied to the
target namespace set ``targetSecret.labels``.

```
apiVersion: failk8s.dev/v1alpha1
kind: SecretCopierConfig
metadata:
  name: registry-credentials
spec:
  rules:
  - sourceSecret:
      name: registry-credentials
      namespace: registry
    targetSecret:
      labels:
        failk8s-pull-secret: "yes"
```

To only have the secret copied to a select list of namespaces based on name,
set ``targetNamespaces.nameSelector``.

```
apiVersion: failk8s.dev/v1alpha1
kind: SecretCopierConfig
metadata:
  name: registry-credentials
spec:
  rules:
  - sourceSecret:
      name: registry-credentials
      namespace: registry
    targetNamespaces:
      nameSelector:
        matchNames:
        - example-1
        - example-2
```

Alternatively, you can match on labels on the namespace by setting a
``targetNamespaces.labelSelector``.

```
apiVersion: failk8s.dev/v1alpha1
kind: SecretCopierConfig
metadata:
  name: registry-credentials
spec:
  rules:
  - sourceSecret:
      name: registry-credentials
      namespace: registry
    targetNamespaces:
      labelSelector:
        matchLabels:
          developer-namespace: "yes"
```

The ``rules`` property is a list, so rules for more than one rule
can technically be specified in the one custom resource.

To setup injection of secrets as an image pull secret against a service
account a custom resource exists called ``SecretInjectorConfig``. You can
create more than one of this type of resource.

Note that nothing is done to validate the secret is of the correct type
before it is added as an image pull secret in the service account.

First example below will inject the named secrets when created in any
namespace, into all service accounts in the same namespace as the secret.
The names of the secrets is given by setting ``sourceSecrets.nameSelector``.

```
apiVersion: failk8s.dev/v1alpha1
kind: SecretInjectorConfig
metadata:
  name: registry-credentials
spec:
  rules:
  - sourceSecrets:
      nameSelector:
        matchNames:
        - registry-credentials
```

If you only want the secret injected into the ``default`` service account
set ``serviceAccounts.nameSelector``.

```
apiVersion: failk8s.dev/v1alpha1
kind: SecretInjectorConfig
metadata:
  name: registry-credentials
spec:
  rules:
  - sourceSecrets:
      nameSelector:
        matchNames:
        - registry-credentials
    serviceAccounts:
      nameSelector:
        matchNames:
        - default
```

Labels can instead be used on both the source secret and service accounts
using ``sourceSecrets.labelSelector`` and ``serviceAccounts.labelSelector``.

```
apiVersion: failk8s.dev/v1alpha1
kind: SecretInjectorConfig
metadata:
  name: registry-credentials
spec:
  rules:
  - sourceSecrets:
      labelSelector:
        matchLabels:
          image-pull-secret: "yes"
    serviceAccounts:
      labelSelector:
        matchLabels:
          inject-image-pull-secrets: "yes"
```

You can be selective about what namespaces injection is performed. This can
be done specifying the names of the namespaces using
``targetNamespaces.nameSelector``:

```
apiVersion: failk8s.dev/v1alpha1
kind: SecretInjectorConfig
metadata:
  name: registry-credentials
spec:
  rules:
  - sourceSecrets:
      nameSelector:
        matchNames:
        - registry-credentials
    targetNamespaces:
      nameSelector:
        matchNames:
        - developer-1
        - developer-2
```

or labels by setting ``targetNamespaces.labelSelector``:

```
apiVersion: failk8s.dev/v1alpha1
kind: SecretInjectorConfig
metadata:
  name: registry-credentials
spec:
  rules:
  - sourceSecrets:
      nameSelector:
        matchNames:
        - registry-credentials
    targetNamespaces:
      labelSelector:
        matchLabels:
          developer-namespace: "yes"
```

The ``rules`` property is a list, so rules for more than one rule
can technically be specified in the one custom resource.
