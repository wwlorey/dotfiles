. $HOME/.bashrc
. $HOME/.config/git-prompt

# Truncate username in command prompt
PS1='%4>>%n%<<@%m %B%1~%b %B%F{blue}>%f%b '

# Configure git prompt
GIT_PS1_SHOWDIRTYSTATE=1
GIT_PS1_SHOWCOLORHINTS=1
precmd () { RPROMPT=$(__git_ps1 " (%s)") }

# Enable autocomplete
autoload -U compinit; compinit
# Enable autocomplete for hidden files
_comp_options+=(globdots)

