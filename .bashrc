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
alias gcp='git cherry-pick'
alias gd='git diff'
alias gdi='git diff --ignore-space-change'
alias gds='git diff --staged'
alias gdss='git diff --staged --stat'
alias gfuz='git-checkout-fuzzy'
alias gl='git log --graph'
alias glp='git log --patch'
alias gpul='git pull'
alias gpus='git push'
alias gpusi='git-push-init'
alias gs='git status'
alias gsh='git stash'
alias gshk='git stash --keep-index'
alias gshl='git stash list'
alias gshp='git stash pop'
alias gsmui='git submodule update --init'

# Ask for consent & be verbose
# These aliases can be ignored by prepending "\" (i.e. "\rm")
alias rm='rm -iv'
alias cp='cp -iv'
alias mv='mv -iv'

alias v='nvim'
alias ev='nvim $HOME/Repos/dotfiles/.config/nvim/init.vim'

alias t='tmux'
alias et='nvim $HOME/Repos/dotfiles/.config/tmux/tmux.conf'
alias ta='tmux attach'

alias eb='nvim $HOME/Repos/dotfiles/.bashrc'
alias ez='nvim $HOME/Repos/dotfiles/.zshrc'

alias hs='hugo server --noHTTPCache'

# Convert document to PDF
alias pdf='unoconv -f pdf'

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

# https://vi.stackexchange.com/questions/7112/tmux-messing-with-vim-highlighting
if [[ $TERM == alacritty ]]; then TERM=xterm-256color; fi

# Use vi-style command line editing
set -o vi

