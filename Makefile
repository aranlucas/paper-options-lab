.PHONY: dev

PYTHON ?= .venv/bin/python

dev:
	portless run --name paper-options-lab $(PYTHON) -m options_lab serve
