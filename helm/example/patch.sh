#!/bin/bash

cat <&0 > .rendered.helm.yaml
kubectl -n example kustomize --enable-alpha-plugins . && rm .rendered.helm.yaml
