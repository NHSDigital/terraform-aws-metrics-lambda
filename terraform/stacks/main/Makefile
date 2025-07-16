SHELL:=/bin/bash -o pipefail -O globstar
.SHELLFLAGS = -ec

list:
	@grep '^[^#[:space:]].*:' Makefile

guard-%:
	@ if [ "${${*}}" = "" ]; then \
		echo "Environment variable $* not set"; \
		exit 1; \
	fi
########################################################################################################################
##
## Makefile for managing account terraform
##
########################################################################################################################

tf-command := apply
application := <replace-me>
stack := main
deployment := main
init := 1
local := 0
exittf := 0
justecho := 0
space := $(empty) $(empty)
plugin_cache_dir ?= $$HOME/.terraform.d/plugin-cache
plan_file:= ./.terraform/terraform.tfplan
vars := -var=account=$(account) -var=application=$(application) -var=stack=$(stack) -var=deployment=$(deployment) -var-file=../../vars/account/$(account).tfvars -var-file=../../vars/external-vars.json
backend_no_lock := -backend-config=bucket=nhse-odin-$(account)-terraform -backend-config=key=$(application)/$(stack)/$(deployment).tfstate -backend-config=skip_credentials_validation=true
backend := $(backend_no_lock) -backend-config=dynamodb_table=nhse-odin-$(account)-terraform
args?=
extra_args?=

guard-%:
	@ if [ "${${*}}" = "" ]; then \
        echo "Environment variable $* not set"; \
        exit 1; \
    fi

required-vars: guard-account guard-application guard-stack guard-deployment

local: required-vars
	@$(eval local := 1)
	@$(eval vars:=$(vars) -var="profile=odin_$(account)")
	@$(eval backend:=$(backend) -backend-config="profile=odin_$(account)")
	@$(eval backend_no_lock:=$(backend_no_lock) -backend-config="profile=odin_$(account)")
	@if [ $(local) -eq 1 ]; then \
		echo "local mode ..."; \
	fi

clean:
	rm -f .terraform.plan 2>/dev/null || true
	rm -rf .terraform 2>/dev/null || true
	rm -rf terraform.tfstate.d 2>/dev/null || true
	rm -f errored.tfstate 2>/dev/null || true
	rm -f .tfplan.exit 2>/dev/null || true

run: required-vars
	@echo "running: terraform $(tf-command) $(vars) $(extra_args) $(args) "; \
	if [ $(justecho) -eq 1 ]; then \
	  	echo justecho=${justecho} init=${init} vars=\"${vars}\" backend=\"${backend}\" extra_args=\"${extra_args}\" args=\"${args}\"; \
		exit 0; \
	fi; \
	exitcode=0;terraform $(tf-command) $(vars) $(extra_args) $(args) || exitcode=$$?; \
	if [ $(exittf) -eq 0 ] || [ "$(tf-command)" != "plan" ]; then \
		exit $$exitcode; \
	fi; \
	echo -n "$${exitcode}" > .tfplan.exit; \
	if [ "$${exitcode}" != "2" ]; then \
		exit $$exitcode; \
	fi;
	@echo "plan successful... check  .tfplan.exit for changes"

init: required-vars
	@if [ $(init) -eq 1 ]; then \
  		echo "running terraform init $(vars) $(backend)"; \
  		if [ $(justecho) -eq 1 ]; then \
  		  	echo justecho=${justecho} init=${init} vars=\"${vars}\" backend=\"${backend}\"; \
  			exit 0; \
		fi; \
  		export TF_PLUGIN_CACHE_DIR="$(plugin_cache_dir)"; \
  		mkdir -p "$(plugin_cache_dir)"; \
		terraform init $(vars) $(backend); \
	fi

echo:
	@$(eval justecho := 1)
	@echo -n ""

no-input:
	@$(eval extra_args += -input=false)
	@echo -n ""

init-upgrade: backend += -upgrade
init-upgrade: init

init-no-backend:
	terraform init -backend=false

init-upgrade-no-backend:
	terraform init -backend=false -upgrade

lock:
	terraform providers lock -platform=linux_amd64

dist-plugins:
	terraform providers mirror ../../../dist/terraform.d/plugins

no-init: init=0
no-init: run

import: tf-command=import
import: init=0
import: run

apply: tf-command=apply
apply: init run

output: tf-command=output
output: vars=
output: init=0
output: init run

plan: tf-command=plan
plan: extra_args += -out $(plan_file)
plan: init run

plan-no-init: init=0
plan-no-init: plan

plan-exit-code-tf: exittf=1
plan-exit-code-tf: extra_args += -detailed-exitcode
plan-exit-code-tf: plan

plan-exit-code-tf-no-init: init=0
plan-exit-code-tf-no-init: plan-exit-code-tf

show-plan:
	terraform show $(plan_file)

plan-no-lock: tf-command=plan
plan-no-lock: extra_args += -lock=false
plan-no-lock: init run

plan-no-init-no-lock: init=0
plan-no-init-no-lock: plan-no-lock

apply-plan: init=0
apply-plan: vars=
apply-plan: extra_args += $(plan_file)
apply-plan: run

refresh: tf-command=apply
refresh: extra_args += -refresh-only
refresh: init run

refresh-no-init: init=0
refresh-no-init: refresh

console: tf-command=console
console: init run

console-no-init: init=0
console-no-init: console
