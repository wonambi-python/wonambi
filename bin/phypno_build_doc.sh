#!/bin/bash

rm ../doc/* -fr
/usr/share/sphinx/scripts/python3/sphinx-apidoc -F -o ../doc/ ../phypno/
cp conf.py ../doc
cd ../doc
make html
