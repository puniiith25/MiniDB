.PHONY: all test verify demo benchmark server cli web clean

PYTHON ?= python3

all: verify test

verify:
	PYTHONPATH=src $(PYTHON) scripts/verify_zero_deps.py

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

demo:
	PYTHONPATH=src $(PYTHON) scripts/demo.py

benchmark:
	PYTHONPATH=src $(PYTHON) scripts/benchmark.py

server:
	PYTHONPATH=src $(PYTHON) -m minidb.server

cli:
	PYTHONPATH=src $(PYTHON) -m minidb

web:
	PYTHONPATH=src $(PYTHON) -m minidb.web

clean:
	rm -rf data/*.db data/*.wal data/*.log
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
