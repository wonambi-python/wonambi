# ~/.bashrc: executed by bash(1) for non-login shells.

[[ $- != *i* ]] && return

alias ls='ls --color=auto'
PS1='[\u@\h:\w]\$ '

export R_LIBS_USER=~/tools/R

export PATH=$PATH:~/tools/dcm2nii

# added by Miniconda3 4.3.11 installer
export PATH="/Fridge/users/giovanni/tools/miniconda3/bin:$PATH"
