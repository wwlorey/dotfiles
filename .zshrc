# https://github.com/ohmyzsh/ohmyzsh
export ZSH=$HOME/.oh-my-zsh

# https://github.com/reobin/typewritten
TYPEWRITTEN_SYMBOL=">"
fpath+=$HOME/.zsh/typewritten
autoload -U promptinit; promptinit
prompt typewritten

plugins=(
    git
    history-substring-search
    npm
)

source $ZSH/oh-my-zsh.sh
