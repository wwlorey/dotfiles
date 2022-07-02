. $HOME/.bashrc
. $HOME/.config/git-prompt

# Set command prompt and truncate username
PS1='%F{yellow}%4>>%n%<<%f%F{blue}@%f%F{red}%m%f %B%1~%b %B%F{blue}>%f%b '

# Automatically cd into typed directory
setopt autocd

# Autocomplete with tab support
autoload -U compinit
zstyle ':completion:*' menu select
zmodload zsh/complist
compinit
_comp_options+=(globdots) # Include hidden files

# Use vim keys in tab complete menu
bindkey -M menuselect 'h' vi-backward-char
bindkey -M menuselect 'k' vi-up-line-or-history
bindkey -M menuselect 'l' vi-forward-char
bindkey -M menuselect 'j' vi-down-line-or-history

# Fix vi mode bug: https://github.com/spaceship-prompt/spaceship-prompt/issues/91
bindkey "^?" backward-delete-char

# Quickly switch between vi modes
export KEYTIMEOUT=1

# Keep track of history
export HISTSIZE=10000
export SAVEHIST=10000
export HISTFILE=$HOME/.cache/zsh/history

# Git prompt
GIT_PS1_SHOWDIRTYSTATE=1
GIT_PS1_SHOWCOLORHINTS=1
precmd () { RPROMPT=$(__git_ps1 " (%s)") }

# Directory stack
setopt AUTO_PUSHD
setopt PUSHD_IGNORE_DUPS
setopt PUSHD_SILENT
alias ds='dirs -v'
for index ({0..9}) alias '$index'='cd +${index}'; unset index

