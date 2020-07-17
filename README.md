Operator to support failk8s
===========================

For now the operator only handles copying of secrets to namespaces. The
ability to inject secrets into service accounts is still coming.

Accepts a custom resource called ``SecretCopierConfig``. You can create
more than one of this type of resource.

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
