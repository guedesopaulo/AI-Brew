all: deps check test

.PHONY: deps
deps:
	uv sync --locked
	uv run pre-commit install

.PHONY: check
check:
	uv run pre-commit run --all-files

.PHONY: test
test:
	uv run python -m pytest

.PHONY: cov
cov:
	@uv run coverage erase \
	&& uv run coverage run --source=. --branch -m pytest || true \
	&& uv run coverage report --show-missing --skip-covered --include 'tests/*' --fail-under 100 \
	&& uv run coverage report --show-missing --skip-covered

.PHONY: clean
clean:
	rm -rf .venv/ .*_cache/ .coverage *.egg-info/ dist/
	find -type d -name '__pycache__' -exec rm -rf {} +
