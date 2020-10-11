PYTHON = python3


.PHONY: all
all:
	@echo "Nothing to build here"

.PHONY: test
test:                   ##: run tests
	tox -p auto

.PHONY:
coverage:               ##: measure test coverage
	tox -e coverage

# XXX: this was meant for uploading to pypi, but pypi deprecated static
# file hosting and I should switch to ReadTheDocs.org
.PHONY: docs
docs:                   ##: (obsolete) build docs.zip
	rm -rf build/docs
	mkdir -p build/docs
	@$(PYTHON) setup.py --long-description | rst2html --exit-status=2 > build/docs/index.html
	cp example*.png build/docs/
	cd build/docs && zip ../docs.zip *


FILE_WITH_VERSION = imgdiff.py
include release.mk
