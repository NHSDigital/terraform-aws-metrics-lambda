SHELL:=/bin/bash -o pipefail -O globstar
.SHELLFLAGS = -ec
.DEFAULT_GOAL := list

account ?= local
make := make --no-print-directory
kubectl := kubectl --context=$(cluster)
helm := helm --kube-context=$(cluster)
linkerd := linkerd --context=$(cluster)
docker_registry ?= our.ecr.registry
ns := <replace-me>
release := <replace-me>
action := upgrade --install --render-subchart-notes --create-namespace

ifeq ($(account), local)
	kubectl := kubectl
	helm := helm
endif

list:
	@grep '^[^#[:space:]].*:' Makefile

guard-%:
	@if [[ "${${*}}" == "" ]]; then \
		echo "env var: $* not set"; \
		exit 1; \
	fi

$(cluster)-external-vars.yaml:
	@if [[ "$(cluster)" != "fake" ]]; then \
  		cluster=$(cluster) $(make) external-vars; \
  	fi


external-vars: guard-cluster
	cluster=$(cluster) ansible-playbook -i localhost, ../ansible/$(release)-external-vars.yml


kustomization :=
ifneq ("$(wildcard kustomization.all.yaml)", "")
kustomization=kustomization.all.yaml
endif
ifneq ("$(account)", "local")
ifneq ("$(wildcard kustomization.nonlocal.yaml)", "")
kustomization=kustomization.nonlocal.yaml
endif
endif
ifneq ("$(wildcard kustomization.$(account).yaml)", "")
kustomization=kustomization.$(account).yaml
endif

kustomization.yaml:
	@if [ -n "$(kustomization)" ]; then \
		cat $(kustomization) | docker_registry=$(docker_registry) envsubst '$${docker_registry}' > kustomization.yaml; \
  	else \
  	  	echo 'no kustomization source file found'; exit 1; \
  	fi

values :=
ifneq ("$(wildcard values.yaml)", "")
values+= -f values.yaml
endif
ifneq ("$(account)", "local")
ifneq ("$(wildcard env/nonlocal.values.yaml)", "")
values+= -f env/nonlocal.values.yaml
endif
endif
ifneq ("$(wildcard env/$(account).values.yaml)", "")
values+= -f env/$(account).values.yaml
endif
ifneq ("$(wildcard env/$(cluster).values.yaml)", "")
values+= -f env/$(cluster).values.yaml
endif
ifneq ("$(wildcard env/$(account).$(cluster).values.yaml)", "")
values+= -f env/$(account).$(cluster).values.yaml
endif

echo:
	@echo "values files: $(values)"; \
	echo "kustomization: $(kustomization)"

namespace:
	if [[ "$(check)" != "yes" ]]; then \
  		if ! $(kubectl) get ns 2>/dev/null | grep -q '^$(ns) '; then $(kubectl) create namespace $(ns); fi; \
		if ! $(kubectl) get ns $(ns) -o yaml | grep -q 'linkerd.io/inject'; then  $(kubectl) annotate ns $(ns) 'linkerd.io/inject=enabled'; fi; \
	fi

apply: guard-cluster guard-account kustomization.yaml $(cluster)-external-vars.yaml namespace
	$(helm) $(action) -n $(ns) --post-renderer ./patch.sh $(values) -f $(cluster)-external-vars.yaml $(release) ./

fake-external-vars:
	@if [ ! -f $(cluster)-external-vars.yaml ]; then \
  		if [ -f .fake-external-vars.yaml ]; then \
  			cp .fake-external-vars.yaml $(cluster)-external-vars.yaml; \
  		else \
  		  touch $(cluster)-external-vars.yaml; \
  		fi; \
	fi

ifeq ("$(cluster)", "")
template-check:
	@cluster=fake $(make) fake-external-vars
	@cluster=fake $(make) template-check
else
template-check: check=yes
template-check: template
endif

template-check-images:
	@$(make) template-check | grep 'image:' | sed -e 's/^[ \t]*//' | sed 's#"##g' | sort -u

template: action:=template
template: apply

debug: action+= --debug
debug: apply

dry-run: action+= --dry-run
dry-run: apply

delete: guard-cluster
	@read -p "this is: $(cluster) are you sure ? (y/n)" confirm; \
	if [[ "$${confirm}" == "y" ]]; then \
		$(helm) uninstall -n $(ns) $(release) || true; \
	fi

update-dependencies: repos
	helm dependency update

build-dependencies: repos
	helm dependency build

rollout-restart-not-running: guard-cluster
	$(kubectl) -n $(ns) get sts --no-headers | grep '0/' | cut -d' ' -f1 | xargs -r $(kubectl) -n $(ns) rollout restart sts || true
	$(kubectl) -n $(ns) get deploy --no-headers | grep '0/' | cut -d' ' -f1 | xargs -r $(kubectl) -n $(ns) rollout restart deploy || true

rollout-restart-sts: guard-cluster
	$(kubectl) -n $(ns) rollout restart sts || true

rollout-restart-deploy: guard-cluster
	$(kubectl) -n $(ns) rollout restart deploy || true

rollout-restart-ds: guard-cluster
	$(kubectl) -n $(ns) rollout restart ds || true

rollout-restart-all: rollout-restart-sts rollout-restart-deploy rollout-restart-ds

rollout-restart-service: guard-cluster guard-service
	$(kubectl) -n $(ns) get ds --no-headers | cut -d' ' -f1 | grep '$(service)' | xargs -r $(kubectl) -n $(ns) rollout restart ds || true
	$(kubectl) -n $(ns) get sts --no-headers | cut -d' ' -f1 | grep '$(service)' | xargs -r $(kubectl) -n $(ns) rollout restart sts || true
	$(kubectl) -n $(ns) get deploy --no-headers | cut -d' ' -f1 | grep '$(service)' | xargs -r $(kubectl) -n $(ns) rollout restart deploy || true

get-all: guard-cluster
	$(kubectl) -n $(ns) get all

get-pods: guard-cluster
	$(kubectl) -n $(ns) get pods

get-deployments: guard-cluster
	$(kubectl) -n $(ns) get deployments

get-statefulsets: guard-cluster
	$(kubectl) -n $(ns) get statefulsets

get-not-running: guard-cluster
	$(kubectl) -n $(ns) get all | grep -v '^service/' | grep '0/'

repos:
	@helm repo list | grep -q 'https://grafana.github.io/helm-charts' || helm repo add grafana https://grafana.github.io/helm-charts
