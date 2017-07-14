## Install matlab_kernel in conda
We need python 3.4 because that the latest python version compatible with matlab 2016a.
```bash
conda create -n py34  python=3.4
source activate py34
```
Then we use `pip`:
```bash
pip install numpy scipy jupyter matlab_kernel
```
Install matlab engine:
```bash
cd /usr/local/matlab/extern/engines/python
python setup.py build --build-base="/home/giovanni/tools/build" install
```

Then install matlab_kernel:
```bash
python -m matlab_kernel install
```
### matlab 2016b
Once we have access to matlab 2016b, maybe it's best to use [imatlab](https://github.com/imatlab/imatlab), so that we can use plotly for interactive plots.

## Install OpenGL and python

### use glumpy

```bash
conda create -n pyqt5
source activate pyqt5
conda install numpy cython
```
The trick is NOT using pyqt5 from conda, because it comes with QT5 which in conda does NOT have opengl.

```bash
pip install sip pyqt5  triangle glumpy
```
### use vispy

```bash
conda create -n vispy
source activate vispy
conda install numpy
```
The trick is NOT using pyqt5 from conda, because it comes with QT5 which in conda does NOT have opengl.

```bash
pip install sip pyqt5 vispy
```
### all together

```bash
conda create -n py36
source activate py36
conda install numpy scipy jupyter 
```

Install all dependencies of jupyter (including qt and pyqt5), then remove them.
The trick is NOT using pyqt5 from conda, because it comes with QT5 which in conda does NOT have opengl.

```bash
conda uninstall qt sip pyqt5
```

```bash
pip install sip pyqt5 vispy phypno
```
