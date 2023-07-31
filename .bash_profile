SCRIPTS_DIR=$HOME/.local/bin

export PATH="$PATH:$SCRIPTS_DIR"
export EDITOR=nvim
export VISUAL=nvim
export BROWSER=brave
export NVM_DIR=$HOME/.nvm
export BAT_THEME=OneHalfDark
export VIMRC=$HOME/.config/nvim/init.vim

# Set fzf to use ripgrep and bat if available
which rg > /dev/null && export FZF_DEFAULT_COMMAND='rg --files --hidden -g "!**/.git/**"'
which bat > /dev/null && 
	export FZF_DEFAULT_OPTS='--preview="bat --color=always --style=numbers --line-range=:500 {}"' || 
	export FZF_DEFAULT_OPTS='--preview="cat {}"'
