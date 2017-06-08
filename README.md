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
