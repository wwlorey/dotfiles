# Pythons older than 3.13 ignore PYTHON_HISTORY and unconditionally write
# ~/.python_history at REPL exit; neutering the writer stops that.
try:
    import readline

    readline.write_history_file = lambda *args, **kwargs: None
except ImportError:
    pass
