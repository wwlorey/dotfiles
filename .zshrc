# https://github.com/ohmyzsh/ohmyzsh
export ZSH=$HOME/.oh-my-zsh

# https://github.com/reobin/typewritten
ZSH_THEME="typewritten/typewritten"
TYPEWRITTEN_SYMBOL=">"

plugins=(
    git
    history-substring-search
    npm
)

source $ZSH/oh-my-zsh.sh
