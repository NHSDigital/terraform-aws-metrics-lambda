SHELL:=/bin/bash -o pipefail -O globstar
.SHELLFLAGS = -ec

make := make --no-print-directory

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

clean:
	find . -type d -name .terraform -exec rm -rf "{}" \; 2>/dev/null || true
	find . -type d -name terraform.tfstate.d -exec rm -rf  "{}" \; 2>/dev/null || true
	find . -name .terraform.plan -type f -delete 2>/dev/null || true
	find . -name errored.tfstate -type f -delete 2>/dev/null || true
	find . -name .tfplan.exit -type f -delete 2>/dev/null || true


external-vars:
	# aws ssm get-parameters --name=/common/static-external-vars --query 'Parameters[0].Value' --output=text >> vars/external-vars.json
	if [ ! -f vars/external-vars.json ]; then \
		echo "{}" > vars/external-vars.json; \
	fi

build:
	mkdir -p ../build/terraform
	cp -r vars ../build/terraform
	cp -r modules ../build/terraform
	cp -r stacks ../build/terraform
	rm -rf ../build/terraform/stacks/local || true
	cp Makefile ../build/terraform
	$(make) -C ../build/terraform external-vars
	$(make) -C ../build/terraform/stacks/main clean init-upgrade-no-backend
