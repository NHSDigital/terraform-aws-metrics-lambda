SHELL:=/bin/bash -o pipefail -O globstar
.SHELLFLAGS = -ec
make := make --no-print-directory
account ?= local
modules := $(shell find . -maxdepth 1 -mindepth 1 -type d -not -path ./ansible -not -path ./local -not -path ./localstack -printf "%p " | sed -E 's#\.|/##g')

list:
	@grep '^[^#[:space:]].*:' Makefile

guard-%:
	@ if [ "${${*}}" = "" ]; then \
	    echo "env var: $* not set"; \
	    exit 1; \
	fi

echo-modules:
	@for folder in $(modules); do \
		echo "$${folder}"; \
	done

clean:
	find . -type d -name charts | xargs -r rm -rf || true
	find . -type f -name external-vars.yaml | xargs -r rm || true
	find . -type f -name *-external-vars.yaml | xargs -r rm || true

build:
	mkdir -p ../build
	cp -r ../helm ../build/helm
	@for module in $(modules); do \
		$(make) -C ../build/helm/$${module} build-dependencies; \
	done

up: guard-account
ifeq ($(account), local)
	$(make) -C localstack up
endif
	@for module in $(modules); do \
		$(make) -C ./$${module} apply; \
	done

down:
	echo "todo"; exit 1
	# Primarily used while debugging

update-dependencies:
ifeq ($(account), local)
	$(make) -C localstack update-dependencies
endif
	@for module in $(modules); do \
		$(make) -C ./$${module} update-dependencies; \
	done

build-dependencies:
ifeq ($(account), local)
	$(make) -C localstack build-dependencies
endif
	@for module in $(modules); do \
		$(make) -C ./$${module} build-dependencies; \
	done

template-check:
ifeq ($(account), local)
	$(make) -C localstack template-check
endif
	@for module in $(modules); do \
		$(make) -C ./$${module} template-check; \
	done


apply: guard-cluster
ifeq ($(cluster), eks-odin)
	$(make) -C example apply
endif


rollout-restart:
ifeq ($(cluster), eks-odin)
	$(make) -C example rollout-restart-sts
	sleep 30
	$(make) -C example rollout-restart-deploy
endif
