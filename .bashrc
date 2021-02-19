# If not running interactively, don't do anything
[[ $- != *i* ]] && return

PS1='[\u@\h \W]\$ '

alias grep='grep --color=auto'
alias ll='ls -la'
alias la='ls -a'

if [[ "$OSTYPE" == "darwin"* ]];
then
	alias ls='ls -G'
else
	alias ls='ls --color=auto'
fi
