# ~/.bashrc: executed by bash(1) for non-login shells.

[[- != *i* ]] && return

alias ls='ls --color=auto'
PS1='[\u@\h:\w]\$ '

export R_LIBS_USER=~/tools/R

export PATH=$PATH:~/tools/dcm2nii

# common folder
export FRIDGE=/Fridge/users/giovanni

# added by Miniconda3 4.3.11 installer
export PATH=$FRIDGE/tools/miniconda3/bin:$PATH

export PYTHONPATH=$FRIDGE/projects/rumc/scripts

#New AFNI path december  2016
## This is basically a copy of /etc/afni/afni.sh, without sourcing the users prefs
## !! note that there is no separate bin/ models/ folder, all is in one. 
#where AFNI is installed
AFNI_INSTALLDIR=/Scratch/AFNI/afni_2016-12-02/linux_fedora_21_64
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
export PATH AFNI_PLUGINPATH AFNI_MODELPATH AFNI_IMSAVE_WARNINGS AFNI_TTATLAS_DATASET
