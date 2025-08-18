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
	rm -rf ./reports
	find . -type d -name '.mypy_cache' | xargs -r rm -r || true

.env:
	touch .env

pytest: .env
	poetry run pytest

test: pytest

reports/:
	mkdir -p reports

coverage: .env
	poetry run pytest --cov --color=yes -v --cov-report=term-missing:skip-covered

coverage-ci: clean .env reports/
	poetry run pytest --cov --color=yes -v --junit-xml=./reports/junit/results.xml --cov-report=term-missing:skip-covered --cov-report xml | tee reports/pytest-coverage.txt

tf-lint:
	tflint --config "$(pwd)/.tflint.hcl"

tf-format-check:
	terraform fmt -check -recursive

tf-format:
	terraform fmt --recursive

tf-trivy:
	trivy conf --exit-code 1 ./ --skip-dirs "**/.terraform" --skip-dirs ".venv"

mypy:
	poetry run mypy .

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

lint: ruff mypy shellcheck

lint-ci: black-check ruff-ci mypy tf-lint tf-trivy shellcheck

check-secrets:
	scripts/check-secrets.sh

check-secrets-all:
	scripts/check-secrets.sh unstaged

check-secrets-history:
	scripts/check-secrets.sh history
