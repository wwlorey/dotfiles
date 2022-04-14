# If not running interactively, don't do anything
[[ $- != *i* ]] && return

PS1='[\u@\h \W]\$ '

alias c='clear'

alias ll='ls -lah'
alias la='ls -a'

alias gb='git branch'
alias gd='git diff'
alias gds='git diff --staged'
alias gl='git log --graph'
alias gs='git status'
alias gcb='git branch --show-current'

alias ci='code-insiders'

# Ask before clobbering
alias rm='rm -i'
alias cp='cp -i'
alias mv='mv -i'

alias grep='grep --color=auto'

if [[ "$OSTYPE" == "darwin"* ]];
then
	alias ls='ls -G'

	# Homebrew's default install location is different on M1 macs: https://apple.stackexchange.com/a/148919
	export PATH="/opt/homebrew/bin:$PATH"

	# nvm is particular
	if [[ -d ~/.nvm ]]
	then
		export NVM_DIR=~/.nvm
		source $(brew --prefix nvm)/nvm.sh
	fi
else
	alias ls='ls --color=auto'
	alias diff='diff --color=auto'

	# XFCE file explorer
	alias fe='thunar'

fi

# Use vi-style command line editing
set -o vi

