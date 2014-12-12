#!/bin/bash
rm .coverage
rm ../test/report -fr
nosetests  ../test/ -A "not gui" --cover-package=phypno --with-coverage --cover-inclusive --cover-html --cover-html-dir=../test/report/

