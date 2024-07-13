import inspect

silent = False

def log_set_silent(s):
    global silent
    silent = s

def log(*args, **kwargs):
    if silent:
        return

    frame = inspect.currentframe().f_back
    module = inspect.getmodule(frame)
    module_name = module.__name__ if module else "__main__"

    message = ' '.join(str(arg) for arg in args)

    # Print the module name followed by the message
    print(f"{module_name}: {message}", **kwargs)
