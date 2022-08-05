PS1='[\u@\h \W]\$ '

alias c='clear'

alias ll='ls -lh'
alias lla='ls -lah'
alias la='ls -a'

alias ga='git add'
alias gaa='git add --all'
alias gb='git branch'
alias gbc='git branch --show-current'
alias gc='git checkout'
alias gcb='git checkout -b'
alias gcm='git commit -m'
alias gd='git diff'
alias gds='git diff --staged'
alias gdss='git diff --staged --stat'
alias gl='git log --graph'
alias gpul='git pull'
alias gpus='git push'
alias gpusi='git-push-init'
alias gs='git status'
alias gsh='git stash'
alias gshl='git stash list'
alias gshp='git stash pop'
alias gsmui='git submodule update --init'

# Ask for consent & be verbose
alias rm='rm -iv'
alias cp='cp -iv'
alias mv='mv -iv'

alias fzf='fzf --preview "bat --color=always --style=numbers --line-range=:500 {}"'

alias ev='nvim $HOME/Repos/dotfiles/.config/nvim/init.vim'

alias venv-activate='. ./venv/bin/activate'
alias venv-deactivate='deactivate'

alias nls='npx lint-staged'

alias python=python3
alias pip=pip3

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

# Load nvm
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"                       # M1 Mac
[ -s "/usr/local/opt/nvm/nvm.sh" ] && \. "/usr/local/opt/nvm/nvm.sh"  # Intel Mac
# Load nvm bash_completion
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"
[ -s "/usr/local/opt/nvm/etc/bash_completion.d/nvm" ] && \. "/usr/local/opt/nvm/etc/bash_completion.d/nvm"
