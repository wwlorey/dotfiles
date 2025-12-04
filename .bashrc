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
alias gcmp='git commit -m prog'
alias gcp='git cherry-pick'
alias gd='git diff'
alias gdi='git diff --ignore-space-change'
alias gds='git diff --staged'
alias gdss='git diff --staged --stat'
alias gfuz='git-checkout-fuzzy'
alias gl='git log --graph'
alias glp='git log --patch'
alias gm='git merge'
alias gpul='git pull'
alias gpus='git push'
alias gpusi='git-push-init'
alias gs='git status'
alias gsh='git stash'
alias gshk='git stash --keep-index'
alias gshl='git stash list'
alias gshp='git stash pop'
alias gsmui='git submodule update --init'

alias r='ranger'

alias n='newsboat'

# Ask for consent & be verbose
# These aliases can be ignored by prepending "\" (i.e. "\rm")
alias rm='rm -iv'
alias cp='cp -iv'
alias mv='mv -iv'

alias v='nvim'
alias ev='$EDITOR $HOME/Repos/dotfiles/.config/nvim/init.vim'

alias t='tmux'
alias et='$EDITOR $HOME/Repos/dotfiles/.config/tmux/tmux.conf'
alias ta='tmux attach'

alias el='$EDITOR $HOME/Repos/dotfiles/.config/lf/lfrc'

alias eb='$EDITOR $HOME/Repos/dotfiles/.bashrc'
alias ez='$EDITOR $HOME/Repos/dotfiles/.zshrc'

alias hs='hugo server --noHTTPCache'

alias lv='link-vid'

alias grep='grep --color=auto'

alias bibcache='rm -rf $(biber --cache)'

alias ws='python3 -m http.server 8000'

alias cb='cargo build'
alias cr='cargo run'
alias ccb='cargo build 2>&1 | tee /dev/tty | pbcopy'

alias g='goose'
alias gsr='goose session --resume'
alias eg='$EDITOR $HOME/Repos/dotfiles/.config/goose/config.yaml'

alias oc='opencode'

alias ti='sh <(curl https://create.tauri.app/sh)' # Initialize Tauri
alias td='pnpm tauri dev'

alias w='work'
alias b='buy'
alias k='keep'

if [[ "$OSTYPE" == "darwin"* ]];
then
	alias ls='ls -G'

	alias o='open'
else
	alias ls='ls --color=auto'
	alias diff='diff --color=auto'

	# XFCE file explorer
	alias fe='thunar'
fi

# https://vi.stackexchange.com/questions/7112/tmux-messing-with-vim-highlighting
if [[ $TERM == alacritty ]]; then export TERM=xterm-256color; fi

# Use vi-style command line editing
set -o vi

