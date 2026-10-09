.PHONY: dev dev-direct

PYTHON ?= .venv/bin/python

dev:
	portless run --name paper-options-lab $(PYTHON) -m options_lab serve

dev-direct:
	$(PYTHON) -m options_lab serve
