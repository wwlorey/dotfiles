# If not running interactively, don't do anything
[[ $- != *i* ]] && return

PS1='[\u@\h \W]\$ '

alias grep='grep --color=auto'
alias ls='ls --color=auto'
alias ll='ls -la'
alias la='ls -a'
