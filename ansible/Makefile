SHELL:=/bin/bash -o pipefail -O globstar
.SHELLFLAGS = -ec
.DEFAULT_GOAL := list

########################################################################################################################
##
## Makefile for managing ansible commands
##
########################################################################################################################

list:
	@grep '^[^#[:space:]].*:' Makefile

guard-%:
	@ if [ "${${*}}" = "" ]; then \
	    echo "Environment variable $* not set"; \
	    exit 1; \
	fi

CHECK := $(if ${CHECK},--check , )

build-ecr-images:
	@poetry run ansible-playbook -i local, playbooks/build-ecr-images.yml

build-and-push-ecr-images:
	@DOCKER_PUSH=yes poetry run ansible-playbook -i local, playbooks/build-ecr-images.yml

build-and-push-latest-ecr-images:
	@DOCKER_PUSH=yes PUSH_CACHE=yes account=$(account) poetry run ansible-playbook -i local, playbooks/build-ecr-images.yml

terraform-external-vars: guard-OUTPUT_DIR
	# record the least changed build versions
	poetry run ansible-playbook -i local, --diff $(CHECK) playbooks/terraform-external-vars.yml
