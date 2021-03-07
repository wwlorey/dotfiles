# If not running interactively, don't do anything
[[ $- != *i* ]] && return

PS1='[\u@\h \W]\$ '

alias ll='ls -la'
alias la='ls -a'

# Ask before clobbering
alias rm='rm -i'
alias cp='cp -i'
alias mv='mv -i'

# Colored command output
alias grep='grep --color=auto'
alias diff='diff --color=auto'
if [[ "$OSTYPE" == "darwin"* ]];
then
	alias ls='ls -G'
else
	alias ls='ls --color=auto'
fi

# Use vi-style command line editing
set -o vi
