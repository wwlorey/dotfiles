export PATH="$PATH:$HOME/.local/bin"
export EDITOR="nvim"
export BROWSER="brave"

if [[ "$OSTYPE" == "darwin"* ]];
then
	# Mac throws a warning when bash is the default shell
	export BASH_SILENCE_DEPRECATION_WARNING=1

	# Homebrew's default install location is different on M1 macs: https://apple.stackexchange.com/a/148919
	export PATH="/opt/homebrew/bin:$PATH"

	which init-stellar-profile > /dev/null && . init-stellar-profile || echo "Failed to initialize Stellar profile."
else
	export TERMINAL="gnome-terminal"

fi

[[ -f ~/.bashrc ]] && . ~/.bashrc

