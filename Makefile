PYTHON = python

FILE_WITH_VERSION = imgdiff.py
FILE_WITH_CHANGELOG = CHANGES.rst


.PHONY: default
default:
	@echo "Nothing to build here"

.PHONY: preview-pypi-description
preview-pypi-description:
	# pip install restview, if missing
	restview --long-description

.PHONY: test check
test:
	$(PYTHON) tests.py
check:
	tox -p auto

.PHONY:
coverage:
	tox -e coverage

# XXX: this was meant for uploading to pypi, but pypi deprecated static
# file hosting and I should switch to ReadTheDocs.org
.PHONY: docs
docs:
	rm -rf build/docs
	mkdir -p build/docs
	@$(PYTHON) setup.py --long-description | rst2html --exit-status=2 > build/docs/index.html
	cp example*.png build/docs/
	cd build/docs && zip ../docs.zip *


include release.mk
