# ---------------------------------------------------------------------------
# Pacman - 42 project
# ---------------------------------------------------------------------------

RUN     := uv run
ENTRY   := pac-man.py
CONFIG  ?= config/config.json

MYPY_FLAGS := --warn-return-any \
              --warn-unused-ignores \
              --ignore-missing-imports \
              --disallow-untyped-defs \
              --check-untyped-defs

.DEFAULT_GOAL := help
.PHONY: help install run debug clean lint lint-strict test package

help:
	@echo "install      Install project dependencies from uv.lock"
	@echo "run          Run the game        (make run CONFIG=path.json)"
	@echo "debug        Run the game in pdb (make debug CONFIG=path.json)"
	@echo "clean        Remove caches and Python artifacts"
	@echo "lint         Run flake8 and mypy"
	@echo "lint-strict  Run flake8 and mypy --strict"
	@echo "test         Run the test suite"
	@echo "package      Build a standalone bundle in dist/PACMAN42/ (PyInstaller)"

install:
	uv sync

run:
	$(RUN) python $(ENTRY) $(CONFIG)

debug:
	$(RUN) python -m pdb $(ENTRY) $(CONFIG)

clean:
	@find . -path ./.venv -prune -o -type d -name '__pycache__' -exec rm -rf {} +
	@rm -rf .mypy_cache .pytest_cache build dist
	@find . -type f -name '*Zone.Identifier*' -delete
	@echo "Cleaned."

lint:
	$(RUN) flake8 .
	$(RUN) mypy . $(MYPY_FLAGS)

lint-strict:
	$(RUN) flake8 .
	$(RUN) mypy . --strict

test:
	$(RUN) pytest

package:
	$(RUN) pyinstaller --noconfirm pacman.spec
	@echo ""
	@echo "Bundle ready: dist/PACMAN42/"
	@echo "Publish:      butler push dist/PACMAN42 <user>/pacman:linux"