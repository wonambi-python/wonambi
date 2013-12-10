#!/bin/bash

rm ../doc/*
sphinx-apidoc -F -o ../doc/ ../phypno/
cp conf.py ../doc
cd ../doc
make html
