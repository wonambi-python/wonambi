# Makefile for phypno upload and documentation
#

# You can set these variables from the command line.
DOCSDIR       = docs
BUILDDIR      = $(DOCSDIR)/build
SOURCEDIR     = $(DOCSDIR)/source
TESTDIR       = tests


# Internal variables.
ALLSPHINXOPTS   = -d $(BUILDDIR)/doctrees $(SOURCEDIR)

.PHONY: help
help:
	@echo "Please use \`make <target>' where <target> is one of"
	@echo "  sdist      prepare distribution of package"
	@echo "  upload     sdist and upload to pypi"
	@echo "  clean      to clean the whole directory"
	@echo "  apidoc     generate api from functions"
	@echo "  html       to make standalone HTML files"
	@echo "  upload_doc upload documentation"
	@echo "  test       run tests"

.PHONY: sdist
sdist:
	python setup.py sdist

.PHONY: upload
upload:
	python setup.py sdist upload

.PHONY: clean
clean:
	rm -rf $(BUILDDIR)/*
	rm $(SOURCEDIR)/auto_examples -fr
	rm $(SOURCEDIR)/modules -fr
	rm $(DOCSDIR)/examples -fr
	rm $(DOCSDIR)/modules -fr

.PHONY: apidoc
apidoc:
	sphinx-apidoc -f -M -e -o $(SOURCEDIR)/api phypno phypno/widgets phypno/scroll_data.py

.PHONY: html
html:
	sphinx-build -b html $(ALLSPHINXOPTS) $(BUILDDIR)/html
	@echo
	@echo "Build finished. The HTML pages are in $(BUILDDIR)/html."

.PHONY: upload_doc	
upload_doc:
	scp -r $(BUILDDIR)/* gpiantoni:public_html/phypno

.PHONY: test
test:
	cd tests; py.test --cov=phypno --cov-report html
