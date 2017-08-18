PHONY = help release sdist upload clean html test

# Makefile for wonambi upload and documentation

DOCSDIR       = docs
BUILDDIR      = $(DOCSDIR)/build
SOURCEDIR     = $(DOCSDIR)/source
TESTDIR       = tests
VERSION       = $(shell grep -Eow "[0-9]+.[0-9]+" -m 1 CHANGES.rst)
COMMENT       = $(subst : ,,$(shell grep -Eo ": .*" -m 1 CHANGES.rst))
ALLSPHINXOPTS   = -d $(BUILDDIR)/doctrees $(SOURCEDIR)

help:
	@echo "Use \`make <target>' where <target> is one of"
	@echo "  tag        edit CHANGES.rst and upload a new tag (travis then uploads to pypi)"
	@echo "  sdist      sdist and upload to pypi"
	@echo "  release    edit CHANGES.rst and upload to github/pypi"
	@echo "  html       to make standalone HTML files"
	@echo "  test       run tests"
	@echo "  clean      to clean the whole directory"

tag:
	echo $(VERSION) > wonambi/VERSION
	git amend
	git tag -a v$(VERSION) -m "$(COMMENT)"
	git push origin --tags
	git push origin master -f

sdist:
	python setup.py sdist upload

# release should not be necessary, because now travis takes care of it
release: tag sdist

# apidoc is now run inside sphinx-build
html:
	sphinx-build -T -b html $(ALLSPHINXOPTS) $(BUILDDIR)/html
	@echo
	@echo "Build finished. The HTML pages are in $(BUILDDIR)/html."

test:
	pytest --cov=wonambi --cov-report html tests

clean:
	rm -fr htmlcov
	rm -rf $(SOURCEDIR)/api
	rm -fr $(SOURCEDIR)/gui/images/
	rm -rf $(BUILDDIR)/*

