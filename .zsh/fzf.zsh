if [[ $(uname) == 'Darwin' ]]; then
    if [[ $(uname -p) == 'i386' ]]; then
        # Intel Mac

        if [[ ! "$PATH" == */usr/local/opt/fzf/bin* ]]; then
            export PATH="${PATH:+${PATH}:}/usr/local/opt/fzf/bin"
        fi

        # Auto-completion
        [[ $- == *i* ]] && source "/usr/local/opt/fzf/shell/completion.zsh" 2> /dev/null

        # Key bindings
        source "/usr/local/opt/fzf/shell/key-bindings.zsh"
    else
        # M1 Mac

        if [[ ! "$PATH" == */opt/homebrew/opt/fzf/bin* ]]; then
            export PATH="${PATH:+${PATH}:}/opt/homebrew/opt/fzf/bin"
        fi

        # Auto-completion
        [[ $- == *i* ]] && source "/opt/homebrew/opt/fzf/shell/completion.zsh" 2> /dev/null

        # Key bindings
        source "/opt/homebrew/opt/fzf/shell/key-bindings.zsh"
    fi
else
    # Assume Linux

    # Auto-completion
    [[ $- == *i* ]] && source "/usr/share/fzf/completion.zsh" 2> /dev/null

    # Key bindings
    source "/usr/share/fzf/key-bindings.zsh"
fi

