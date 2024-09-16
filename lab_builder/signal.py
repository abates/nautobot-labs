INITIALIZED = "initialized"
START = "start"
STARTED = "started"
STOP = "stop"
STOPPED = "stopped"
DESTROY = "destroy"
DESTROYED = "destroyed"

def emit(signal, *objs):
    for obj in objs:
        if hasattr(obj, signal):
            getattr(obj, signal)()
        children = getattr(obj, "children", None)
        if children:
            emit(signal, *children)
