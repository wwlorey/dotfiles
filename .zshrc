# https://github.com/ohmyzsh/ohmyzsh
export ZSH="~/.oh-my-zsh"

# https://github.com/reobin/typewritten
TYPEWRITTEN_SYMBOL=">"
fpath+=~/.zsh/typewritten
autoload -U promptinit; promptinit
prompt typewritten

plugins=(git osx)
