apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: secretinjectorconfigs.failk8s.dev
spec:
  scope: Cluster
  group: failk8s.dev
  names:
    plural: secretinjectorconfigs
    singular: secretinjectorconfig
    kind: SecretInjectorConfig
    categories:
    - failk8s-operator
  versions:
    - name: v1alpha1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              properties:
                rules:
                  type: array
                  items:
                    type: object
                    required:
                    - sourceSecrets
                    properties:
                      targetNamespaces:
                        type: object
                        properties:
                          nameSelector:
                            type: object
                            required:
                            - matchNames
                            properties:
                              matchNames:
                                type: array
                                items:
                                  type: string
                          labelSelector:
                            type: object
                            required:
                            - matchLabels
                            properties:
                              matchLabels:
                                type: object
                                x-kubernetes-preserve-unknown-fields: true
                      sourceSecrets:
                        type: object
                        oneOf:
                        - required:
                          - nameSelector
                        - required:
                          - labelSelector
                        properties:
                          nameSelector:
                            type: object
                            required:
                            - matchNames
                            properties:
                              matchNames:
                                properties:
                                  type: array
                                  items:
                                    type: string
                            labelSelector:
                            type: object
                            required:
                            - matchLabels
                            properties:
                              matchLabels:
                                type: object
                                x-kubernetes-preserve-unknown-fields: true
                      serviceAccounts:
                        type: object
                        properties:
                          nameSelector:
                            type: object
                            required:
                            - matchNames
                            properties:
                              matchNames:
                                type: array
                                items:
                                  type: string
                          labelSelector:
                            type: object
                            required:
                            - matchLabels
                            properties:
                              matchLabels:
                                type: object
                                x-kubernetes-preserve-unknown-fields: true
