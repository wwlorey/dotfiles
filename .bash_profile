SCRIPTS_DIR=$HOME/.local/bin

export PATH="$PATH:$SCRIPTS_DIR"
export EDITOR=nvim
export VISUAL=nvim
export BROWSER=brave
export BAT_THEME=OneHalfDark
export VIMRC=$HOME/.config/nvim/init.vim

which init-openai > /dev/null && source init-openai

# fzf: use fd and bat if available
which fd > /dev/null &&
  export FZF_DEFAULT_COMMAND='fd --type file --hidden --exclude .git' ||
  echo "Note: fd not installed."
which bat > /dev/null && 
	export FZF_DEFAULT_OPTS='--preview="bat --color=always --style=numbers --line-range=:500 {}"' || 
	echo "Note: bat not installed." && export FZF_DEFAULT_OPTS='--preview="cat {}"'

yabai --start-service
skhd --start-service
