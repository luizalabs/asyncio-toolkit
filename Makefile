.PHONY: help

help:  ## This help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

clean: ## Clean cache and temporary files
	@find . -name "*.pyc" | xargs rm -rf
	@find . -name "*.pyo" | xargs rm -rf
	@find . -name "__pycache__" -type d | xargs rm -rf
	@rm -rf *.egg-info
	@rm -f .coverage

lint:  ## Run static code checks
	@flake8 .
	@isort --check

test: clean ## Run unit tests
	@py.test -xs tests/

test-matching: clean ## Search and run unit test
	@py.test -xs tests/ -k $(Q)

coverage:  ## Run unit tests and generate code coverage report
	@py.test -xs --cov asyncio_toolkit/ --cov-report=xml --cov-report=term-missing tests/

install:  ## Install development dependencies
	@pip install -r requirements-dev.txt

PHONY: release-patch
# target: release-patch - Release a patch version
release-patch:
	bumpversion patch

PHONY: release-minor
# target: release-minor - Release a minor version
release-minor:
	bumpversion minor

PHONY: release-major
# target: release-major - Release a major version
release-major:
	bumpversion major

packaging: # publish
	python setup.py sdist bdist_wheel upload -r pypi
