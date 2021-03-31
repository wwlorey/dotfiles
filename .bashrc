# If not running interactively, don't do anything
[[ $- != *i* ]] && return

PS1='[\u@\h \W]\$ '

alias c='clear'

alias ll='ls -la'
alias la='ls -a'

alias gb='git branch'
alias gd='git diff'
alias gl='git log --graph'
alias gs='git status'

# Ask before clobbering
alias rm='rm -i'
alias cp='cp -i'
alias mv='mv -i'

# Colored command output
alias grep='grep --color=auto'
if [[ "$OSTYPE" == "darwin"* ]];
then
	alias ls='ls -G'
else
	alias ls='ls --color=auto'
	alias diff='diff --color=auto'
fi

# Use vi-style command line editing
set -o vi
