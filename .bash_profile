export PATH="$PATH:$HOME/.local/bin"
export EDITOR="nvim"
export VISUAL="nvim"
export BROWSER="brave"

if [[ "$OSTYPE" == "darwin"* ]];
then
	# Homebrew's default install location is different on M1 macs: https://apple.stackexchange.com/a/148919
	export PATH="/opt/homebrew/bin:$PATH"

	which init-stellar-profile > /dev/null && . init-stellar-profile || echo "Failed to initialize Stellar profile."
else
	export TERMINAL="gnome-terminal"

fi

