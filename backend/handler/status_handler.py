# handler/status_handler.py

status = {
    "running": False
}

def start():
    status["running"] = True

def stop():
    status["running"] = False

def is_running():
    return status["running"]