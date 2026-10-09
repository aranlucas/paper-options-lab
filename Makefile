.PHONY: dev

PYTHON ?= .venv/bin/python

dev:
	web/node_modules/.bin/portless run --name paper-options-lab $(PYTHON) -m options_lab serve
