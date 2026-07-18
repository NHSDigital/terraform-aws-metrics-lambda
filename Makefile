SHELL:=$(shell which bash) -o pipefail -O globstar
.SHELLFLAGS = -ec
.PHONY: build dist
.DEFAULT_GOAL := list
# this is just to try and supress errors caused by uv run
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

.venv/:
	uv venv --python="$$(python --version | cut -d ' ' -f2)"

install: .venv/
	uv sync --frozen

install-ci:
	uv sync --frozen --no-group local

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
	uv run --frozen pytest

test: pytest

reports/:
	mkdir -p reports

coverage: .env
	uv run --frozen pytest --cov --color=yes -v --cov-report=term-missing:skip-covered

coverage-ci: clean .env reports/
	uv run --frozen pytest --cov --color=yes -v --junit-xml=./reports/junit/results.xml --cov-report=term-missing:skip-covered --cov-report xml | tee reports/pytest-coverage.txt

tf-lint:
	tflint --config "$(pwd)/.tflint.hcl"

tf-format-check:
	terraform fmt -check -recursive

tf-format:
	terraform fmt --recursive

tf-trivy:
	#trivy conf --exit-code 1 ./ --skip-dirs "**/.terraform" --skip-dirs ".venv"

mypy:
	uv run --frozen mypy .

shellcheck:
	@docker run --rm -i -v ${PWD}:/mnt:ro koalaman/shellcheck -f gcc -e SC1090,SC1091 `find . \( -path "*/.venv/*" -prune -o -path "*/build/*" -prune -o -path "*/dist/*" -prune  -o -path "*/.tox/*" -prune \) -o -type f -name '*.sh' -print`

ruff: black
	uv run --frozen ruff check . --fix --show-fixes

ruff-check:
	uv run --frozen ruff check .

ruff-ci:
	uv run --frozen ruff check . --output-format=github

black:
	uv run --frozen black .

black-check:
	uv run --frozen black . --check

lint: ruff mypy shellcheck

lint-ci: black-check ruff-ci mypy tf-lint tf-trivy shellcheck

check-secrets:
	scripts/check-secrets.sh

check-secrets-all:
	scripts/check-secrets.sh unstaged

check-secrets-history:
	scripts/check-secrets.sh history

clean:
	rm -rf ./dist

dist: clean
	rsync -av ./ --exclude .git --exclude .venv --exclude .idea --exclude .github --exclude .pytest_cache --exclude .ruff_cache --exclude __pycache__ --exclude .mypy_cache --exclude dist --exclude reports --exclude tests --exclude scripts --exclude Makefile --exclude sonar-project.properties --exclude '.*' --exclude '*.md' --exclude '*.yaml' --exclude '*.toml' ./ ./dist
	pushd ./dist && zip -r ../dist.zip . && popd
