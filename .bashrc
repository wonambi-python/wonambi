alias ls='ls --color=auto'


source ~/.bashrc_secrets

# R
export R_LIBS_USER=~/tools/Rlib
alias R='R --no-save'

# common folder
export FRIDGE=/Fridge/users/giovanni

# Miniconda3 
# export PATH=~/tools/miniconda/bin:$PATH
# pip3 (instead of miniconda)
export PATH=~/.local/bin:$PATH

export PYTHONPATH=$FRIDGE/projects/rumc/scripts

# matlab
alias matlab=matlab2018a

# nodejs
export NODEJS_HOME=~/tools/node-v8.9.2
export PATH=$NODEJS_HOME/bin:$PATH

# ruby
export GEM_HOME=~/tools/ruby

# fsl
FSLDIR=/usr/local/fsl/6.0.1
. ${FSLDIR}/etc/fslconf/fsl.sh
PATH=${FSLDIR}/bin:${PATH}
export FSLDIR PATH

# mricron (use latest version)
# alias mricron=MRIcron

# freesurfer
export FREESURFER_HOME=/usr/local/freesurfer_6.0.1
export LOCAL_DIR=$FREESURFER_HOME/local
export FSFAST_HOME=$FREESURFER_HOME/fsfast
export MINC_BIN_DIR=$FREESURFER_HOME/mni/bin
export MINC_LIB_DIR=$FREESURFER_HOME/mni/lib
export MNI_DATAPATH=$FREESURFER_HOME/mni/data
export MNI_DIR=$FREESURFER_HOME/mni
export PERL5LIB=$MINC_LIB_DIR/perl5/5.8.5
export FSF_OUTPUT_FORMAT=nii.gz
export PATH=$FREESURFER_HOME/bin:$FSFAST_HOME/bin:$MINC_BIN_DIR:$PATH

export SUBJECTS_DIR=/Fridge/users/giovanni/projects/freesurfer

#New AFNI path december  2016
## This is basically a copy of /etc/afni/afni.sh, without sourcing the users prefs
## !! note that there is no separate bin/ models/ folder, all is in one. 
#where AFNI is installed
AFNI_INSTALLDIR=/usr/local/afni
# AFNI_INSTALLDIR=/Scratch/AFNI/afni_2016-12-02/linux_fedora_21_64
# add the AFNI binary path to the search path
PATH=${AFNI_INSTALLDIR}:${PATH}
# Location of the plugins
AFNI_PLUGINPATH=${AFNI_INSTALLDIR}
# Location of the timseries models (also plugins)
AFNI_MODELPATH=${AFNI_INSTALLDIR}
# Location of the talairach daemon database
AFNI_TTATLAS_DATASET=/usr/share/afni/atlases
#
# Runtime checks
#
# Suppress warning for missing mpeg output
AFNI_IMSAVE_WARNINGS=NO
AFNI_NIFTI_TYPE_WARN=NO
export PATH AFNI_PLUGINPATH AFNI_MODELPATH AFNI_IMSAVE_WARNINGS AFNI_TTATLAS_DATASET AFNI_NIFTI_TYPE_WARN
# ln -s /usr/lib/x86_64-linux-gnu/libgsl.so  /home/giovanni/tools/lib/libgsl.so.0
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/home/giovanni/tools/lib

# ANTS
export PATH=~/tools/ants:$PATH

# custom code (ctags)
export PATH=~/tools/bin:$PATH

# custom firefox
export PATH=~/tools/bin/firefox:$PATH

# custom SQL schema
export PATH=~/tools/bin/schemacrawler:$PATH

sql_schema(){
    schemacrawler.sh -server sqlite -database "$1" -password= -command=schema -outputformat=png -outputfile=sql_schema.png
}

# BIDS validator

bids(){
    docker run -ti --rm -v `readlink -f "$1"`:/data:ro bids/validator --config.ignore=38 --config.ignore=39 --config.ignore=97 /data --verbose
}

# use all colors in MATE terminal
export TERM=xterm-256color
# export TERM=screen-256color

# remember history from all the terminals
export PROMPT_COMMAND='history -a'

alias flywheel="fw login $FLYWHEEL_TOKEN"

# offline export of plotly images
export PATH=$PATH:/home/giovanni/tools/miniconda/lib/orca_app

## >>> conda initialize >>>
## !! Contents within this block are managed by 'conda init' !!
#__conda_setup="$('/home/giovanni/tools/miniconda/bin/conda' 'shell.bash' 'hook' 2> /dev/null)"
#if [ $? -eq 0 ]; then
#    eval "$__conda_setup"
#else
#    if [ -f "/home/giovanni/tools/miniconda/etc/profile.d/conda.sh" ]; then
#        . "/home/giovanni/tools/miniconda/etc/profile.d/conda.sh"
#    else
#        export PATH="/home/giovanni/tools/miniconda/bin:$PATH"
#    fi
#fi
#unset __conda_setup
## <<< conda initialize <<<

# hide conda and venv
PS1='[\u@\h:\w]\$ '
