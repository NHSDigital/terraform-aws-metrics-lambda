SHELL:=/bin/bash -o pipefail -O globstar
.SHELLFLAGS = -ec
.PHONY: build dist
.DEFAULT_GOAL := list
# this is just to try and supress errors caused by poetry run
export PYTHONWARNINGS=ignore:::setuptools.command.install
make := make --no-print-directory

list:
	@grep '^[^#[:space:]].*:' Makefile



guard-%:
	@if [[ "${${*}}" == "" ]]; then \
		echo "env var: $* not set"; \
		exit 1; \
	fi

########################################################################################################################
##
## Makefile for this project things
##
########################################################################################################################
pwd := ${PWD}
dirname := $(notdir $(patsubst %/,%,$(CURDIR)))
DOCKER_BUILDKIT ?= 1

ifneq (,$(wildcard ./.env))
    include .env
    export
endif

install:
	poetry install --sync

install-ci:
	poetry install --without local --sync

local-terraform:
	$(make) -C terraform/stacks/local

clean:
	rm -rf ./build
	rm -rf ./dist
	find . -type d -name '.mypy_cache' | xargs -r rm -r || true

build:
	mkdir -p build
	#$(make) -C ansible build-ecr-images; cp docker/digests.yml ./build
	$(make) -C terraform build

dist: clean build
	mv build dist

pytest: .env
	poetry run pytest tests/unit

test: pytest

integration-test:
	poetry run pytest tests/integration

tf-lint:
	tflint --chdir=terraform/stacks/main --config "$(pwd)/.tflint.hcl"

tf-format-check:
	terraform fmt -check -recursive

tf-format:
	terraform fmt --recursive

tf-trivy:
	trivy conf --exit-code 1 terraform --skip-dirs "**/.terraform" --skip-dirs "stacks/local"

mypy:
	poetry run mypy .

hadolint:
	@docker run --rm -i -v ${PWD}/docker:/docker:ro hadolint/hadolint hadolint --config=docker/hadolint.yml docker/*/Dockerfile | sed 's/:\([0-9]\+\) /:\1:0 /'

shellcheck:
	@docker run --rm -i -v ${PWD}:/mnt:ro koalaman/shellcheck -f gcc -e SC1090,SC1091 `find . \( -path "*/.venv/*" -prune -o -path "*/build/*" -prune -o -path "*/dist/*" -prune  -o -path "*/.tox/*" -prune \) -o -type f -name '*.sh' -print`

ruff: black
	poetry run ruff check . --fix --show-fixes

ruff-check:
	poetry run ruff check .

ruff-ci:
	poetry run ruff check . --output-format=github

black:
	poetry run black .

black-check:
	poetry run black . --check

ansible-lint:
	if find . -type d -name 'ansible' -not -path './.venv/*' -not -path './build/*' -not -path './dist/*' 2> /dev/null | grep -q 'ansible'; then \
		poetry run ansible-lint --force-color -pv `find . -type d -name 'ansible' -not -path './.venv/*' -not -path './build/*' -not -path './dist/*' -printf '%P '`; \
	fi

lint: ruff mypy shellcheck

lint-ci: black-check ruff-ci mypy tf-lint tf-trivy ansible-lint

coverage-cleanup:
	rm -f .coverage* || true

coverage-ci-test: certs
	poetry run coverage run -m pytest tests/integration --color=yes -v --junit-xml=./reports/junit/tests-integration.xml
	poetry run coverage run -a -m pytest tests/mocked --color=yes -v --junit-xml=./reports/junit/tests-mocked.xml

coverage-report:
	@poetry run coverage report; \
	poetry run coverage xml;

coverage: coverage-cleanup coverage-test coverage-report

coverage-test:
	poetry run coverage run -m pytest tests/integration
	poetry run coverage run -a -m pytest tests/mocked

coverage-ci: coverage-cleanup coverage-ci-test coverage-report

check-secrets:
	scripts/check-secrets.sh

check-secrets-all:
	scripts/check-secrets.sh unstaged

docker-login: guard-account
	@aws --profile=odin_$(account) --region=eu-west-2 ecr get-login-password | docker login --username AWS --password-stdin "$$(aws --profile=odin_$(account) sts get-caller-identity --query Account --output text).dkr.ecr.eu-west-2.amazonaws.com"

.env:
	echo "LOCALSTACK_PORT=$$(python -c 'import socket; s=socket.socket(); s.bind(("", 0)); print(s.getsockname()[1])')" > .env

up: .env
	docker compose up -d

down:
	docker compose down

refresh-requirements:
	@find . -type f -name '.lock-hash' | xargs -r rm; \
	$(make) requirements

requirements:
	@lock_hash=$$(md5sum poetry.lock | cut -d' ' -f1); \
	for f in $$(find . -type f -name 'poetry-cmd.sh' | sort); do \
		reqs_dir="$$(dirname $$f)"; \
		echo "$${reqs_dir}"; \
		cmd_hash=$$(md5sum $$f | cut -d' ' -f1) ; \
		cur_hash=$$(cat "$${reqs_dir}/.lock-hash" 2>/dev/null || echo -n ''); \
		update="no"; \
		if test ! -f "$${reqs_dir}/requirements.txt"; then \
		  	echo "$${reqs_dir}/requirements.txt does not exist"; \
		  	update="yes"; \
		fi; \
		if [[ "$${lock_hash}+$${cmd_hash}" != "$${cur_hash}" ]]; then \
		  echo "$${lock_hash}+$${cmd_hash} != $${cur_hash}"; \
		  update="yes"; \
		fi; \
		if [[ "$${update}" == "yes" ]]; then \
		  echo "running: $${f}"; \
		  /bin/bash $$f; \
		  echo -n "$${lock_hash}+$${cmd_hash}" > "$${reqs_dir}/.lock-hash"; \
		else \
		  echo "$${lock_hash}+$${cmd_hash} == $${cur_hash}"; \
		fi \
	done


compare-to: guard-dir
	 diff --exclude='.gitallowed'  --exclude=terraform --exclude='.idea' --exclude='helm'  '--exclude=.venv' '--exclude=.mypy_cache' '--exclude=.ruff_cache' '--exclude=.git' '--exclude=poetry.lock' '--exclude=external-vars.json' --exclude='pyproject.toml' ./ $(dir)
