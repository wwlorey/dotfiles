export PATH="$PATH:$HOME/.local/bin"
export EDITOR="nvim"
export TERMINAL="gnome-terminal"
export BROWSER="brave"

if [[ "$OSTYPE" == "darwin"* ]];
then
	# Mac throws a warning when bash is the default shell
	export BASH_SILENCE_DEPRECATION_WARNING=1
fi

[[ -f ~/.bashrc ]] && . ~/.bashrc
