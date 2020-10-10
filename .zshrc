# https://github.com/ohmyzsh/ohmyzsh
export ZSH=$HOME/.oh-my-zsh

# https://github.com/reobin/typewritten
fpath+=$HOME/.zsh/typewritten
autoload -U promptinit; promptinit
prompt typewritten
ZSH_THEME=""
TYPEWRITTEN_SYMBOL=">"

plugins=(
    git
    history-substring-search
    npm
)

source $ZSH/oh-my-zsh.sh
