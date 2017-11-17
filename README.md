# Python

Default python should rely on miniconda3 (currently python 3.6).
It has quite some useful packages:

 - Qt (v5.6 unfortunately, instead of the current v5.9)
 
 - pandoc (latest version)

 - openGL works fine

## Special Environments

### PyQt5

Conda has Qt5.6, while the latest is Qt5.9.
I tried to uninstall qt, pyqt and sip from conda and install them from pip (to use the system Qt5.9).
However, I get a seg fault when I run wonambi. 
I don't get any error when running it within ipython (`gui qt`) and I don't know how to debug it.

### Install matlab_kernel in conda
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
#### matlab 2016b
Once we have access to matlab 2016b, maybe it's best to use [imatlab](https://github.com/imatlab/imatlab), so that we can use plotly for interactive plots.

# R
Try to download as many packages as possible from anaconda. 
You should not use the system R because you want to install rpy2 using the python installation.
However, some packages, such as circular, requires gcc and fortran used for the original R installation.
This is a pain, because the gcc in conda (gcc_linux-64) messes up all the environmental variables and conda does not have gfortran as executible.

The shortcut is to use the system R to compile the libraries you need, and then use the conda R.
Clearly, this approach will break sooner or later.

## LD_LIBRARY_PATH
To run R, you need some libraries in miniconda, which are not installed automatically when you work with environments, so you need to add this:

```bash
export LD_LIBRARY_PATH=/Fridge/users/giovanni/tools/miniconda3/lib
```

Attention: this might mess up some programs, such as geckodriver.
