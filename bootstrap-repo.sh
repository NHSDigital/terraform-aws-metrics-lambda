#!/usr/bin/env bash

set -euo pipefail

app="${1}"

if [ -z "${app}" ]; then
  echo "usage: "
  echo "    ./bootstrap-repo.sh <app>"
  echo "app is the app suffix .. e.g.  'mimir' for odin-mimir"
  exit 1
fi

find . -type f -not -name 'bootstrap-repo.sh' -not -path './.venv/*' -not -path './.idea/*' -not -path './.git/*' -exec file {} + | awk -F: '/ASCII text/ {print $1}' | xargs -r sed -i "s#odin-template#odin-${app}#g"
find . -type f -not -name 'bootstrap-repo.sh' -not -path './.venv/*' -not -path './.idea/*' -not -path './.git/*' -exec file {} + | awk -F: '/ASCII text/ {print $1}' | xargs -r sed -i -E "s#<?replace-me>?#${app}#g"

mv terraform/modules/example "terraform/modules/${app}"
mv helm/example "helm/${app}"
mv helm/ansible/example-external-vars.yml "helm/ansible/${app}-external-vars.yml"
sed -i "s#/example\"#/${app}\"#g" terraform/stacks/main/main.tf
sed -i "s#/example\"#/${app}\"#g" terraform/stacks/local/main.tf

mv README.tpl.md README.md
rm ./bootstrap-repo.sh
