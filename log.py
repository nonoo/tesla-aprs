silent = False

def log_set_silent(s):
    global silent
    silent = s

def log(*args, **kwargs):
    if not silent:
        print(*args, **kwargs)
