#!/bin/bash
rm .coverage
nosetests  ../test --cover-package=phypno --with-coverage --cover-inclusive --cover-html --cover-html-dir=../test/report/

