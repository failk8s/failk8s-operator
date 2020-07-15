apiVersion: failk8s.dev/v1alpha1
kind: SecretInjectorConfig
metadata:
  name: developer-namespaces
spec:
  rules:
  - targetNamespaces:
      nameSelector:
        matchNames:
        - example-1
        - example-2
      labelSelector:
        matchLabels:
          developer-namespace: "yes"
    sourceSecrets:
      nameSelector:
        matchNames:
        - failk8s-registry-credentials
      labelSelector:
        matchLabels:
          failk8s-pull-secret: "yes"
    serviceAccounts:
      nameSelector:
        matchNames:
        - default
      labelSelector:
        matchLabels:
          failk8s-add-pull-secrets: "yes"
