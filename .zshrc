. $HOME/.bashrc
. $HOME/.zsh/git-prompt
. $HOME/.zsh/fzf.zsh

# Set command prompt and truncate username
PS1='%F{yellow}%4>>%n%<<%f%F{blue}@%f%F{red}%m%f %B%1~%b %B%F{blue}>%f%b '

# Git prompt
GIT_PS1_SHOWDIRTYSTATE=1
GIT_PS1_SHOWCOLORHINTS=1
precmd () { RPROMPT=$(__git_ps1 " (%s)") }

# Keep track of history
export HISTSIZE=10000
export SAVEHIST=10000
export HISTFILE=$HOME/.cache/zsh/history

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

# https://github.com/spaceship-prompt/spaceship-prompt/issues/91
bindkey "^?" backward-delete-char

# Quickly switch between vi modes
export KEYTIMEOUT=1

# Set fzf to use ripgrep if available
which rg > /dev/null && export FZF_DEFAULT_COMMAND='rg --files --hidden -g "!**/.git/**"'

# fzf bindings
bindkey -s '^f' 'cd "$(dirname "$(fzf)")"\n'
bindkey -s '^p' 'fzf | xargs -r $EDITOR\n'

# Change the cursor depending on the vi mode
# Vim control sequences: https://ttssh2.osdn.jp/manual/4/en/usage/tips/vim.html
cursorBlock='\e[2 q'
cursorVertLine='\e[6 q'

zle-line-init() {
    echo -ne $cursorVertLine
}
zle -N zle-line-init

zle-keymap-select() {
    if [[ ${KEYMAP} == vicmd ]] ||
        [[ $1 = 'block' ]]; then
        echo -ne $cursorBlock
    elif [[ ${KEYMAP} == main ]] ||
        [[ ${KEYMAP} == viins ]] ||
        [[ ${KEYMAP} = '' ]] ||
        [[ $1 = 'beam' ]]; then
        echo -ne $cursorVertLine
    fi
}
zle -N zle-keymap-select

# Edit current line in $EDITOR
autoload edit-command-line; zle -N edit-command-line
bindkey '^l' edit-command-line
bindkey -M vicmd '^l' edit-command-line

# Directory stack
setopt AUTO_PUSHD
setopt PUSHD_IGNORE_DUPS
setopt PUSHD_SILENT
alias ds='dirs -v'
for index ({1..9}) alias "$index"="cd +${index}"; unset index

. $HOME/.zsh/plugins/fast-syntax-highlighting/fast-syntax-highlighting.plugin.zsh
. $HOME/.zsh/plugins/zsh-bd/bd.zsh

