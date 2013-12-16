#!/bin/bash
nosetests-3.3 ../test --cover-package=phypno --with-coverage > ../test/log/phypno_p3 2>&1
nosetests-2.7 ../test --cover-package=phypno --with-coverage > ../test/log/phypno_p2 2>&1