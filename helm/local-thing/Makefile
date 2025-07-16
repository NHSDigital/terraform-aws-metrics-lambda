SHELL:=/bin/bash -o pipefail -O globstar
.SHELLFLAGS = -ec
.DEFAULT_GOAL := list

account ?= local
make:= make --no-print-directory

list:
	@grep '^[^#[:space:]].*:' Makefile

guard-%:
	@ if [ "${${*}}" = "" ]; then \
		echo "Environment variable $* not set"; \
		exit 1; \
	fi

apply:
	@echo "pass"

delete:
	@echo "pass"

template-check:
	@echo "pass"

template:
	@echo "pass"

debug:
	@echo "pass"

update-dependencies:
	@echo "pass"

build-dependencies:
	@echo "pass"
