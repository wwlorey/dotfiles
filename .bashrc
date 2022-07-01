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

# Ask for consent & be verbose
alias rm='rm -iv'
alias cp='cp -iv'
alias mv='mv -iv'

alias grep='grep --color=auto'

if [[ "$OSTYPE" == "darwin"* ]];
then
	alias ls='ls -G'

    alias brave='/Applications/Brave\ Browser.app/Contents/MacOS/Brave\ Browser'
else
	alias ls='ls --color=auto'
	alias diff='diff --color=auto'

	# XFCE file explorer
	alias fe='thunar'
fi

# Use vi-style command line editing
set -o vi

# Lazy load nvm (source: http://broken-by.me/lazy-load-nvm/, https://gist.github.com/fl0w/07ce79bd44788f647deab307c94d6922)
lazyLoadNvm() {
    unset -f nvm node npm npx
    export NVM_DIR=~/.nvm
    # Load nvm
    [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
    # Load nvm bash_completion
    if [ -f "$NVM_DIR/bash_completion" ]; then
        [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"
    fi
}

nvm() {
    lazyLoadNvm
    nvm $@
}
 
node() {
    lazyLoadNvm
    node $@
}
 
npm() {
    lazyLoadNvm
    npm $@
}

npx() {
    lazyLoadNvm
    npx $@
}

