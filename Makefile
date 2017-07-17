PHONY = help release sdist upload clean apidoc html test

# Makefile for phypno upload and documentation

DOCSDIR       = docs
BUILDDIR      = $(DOCSDIR)/build
SOURCEDIR     = $(DOCSDIR)/source
TESTDIR       = tests
VERSION       = $(shell grep -Eow "[0-9]+.[0-9]+" -m 1 CHANGES.rst)
COMMENT       = $(subst : ,,$(shell grep -Eo ": .*" -m 1 CHANGES.rst))
ALLSPHINXOPTS   = -d $(BUILDDIR)/doctrees $(SOURCEDIR)

help:
	@echo "Please use \`make <target>' where <target> is one of"
	@echo "  release    edit CHANGES.rst and upload to github/pypi"
	@echo "  tag        edit CHANGES.rst and upload a new tag"
	@echo "  sdist      sdist and upload to pypi"
	@echo "  clean      to clean the whole directory"
	@echo "  apidoc     generate api from functions"
	@echo "  html       to make standalone HTML files"
	@echo "  upload_doc upload documentation"
	@echo "  test       run tests"


release: tag sdist

tag:
	echo $(VERSION) > phypno/VERSION
	git amend
	git tag -a v$(VERSION) -m "$(COMMENT)"
	git push origin --tags

sdist:
	python setup.py sdist upload

clean:
	rm -rf $(BUILDDIR)/*
	rm $(SOURCEDIR)/auto_examples -fr
	rm $(SOURCEDIR)/modules -fr
	rm $(DOCSDIR)/examples -fr
	rm $(DOCSDIR)/modules -fr

apidoc:
	sphinx-apidoc -f -M -e -o $(SOURCEDIR)/api phypno phypno/widgets phypno/scroll_data.py

html:
	sphinx-build -b html $(ALLSPHINXOPTS) $(BUILDDIR)/html
	@echo
	@echo "Build finished. The HTML pages are in $(BUILDDIR)/html."

test:
	cd tests; py.test --cov=phypno --cov-report html
