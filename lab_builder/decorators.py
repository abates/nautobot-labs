
def command(method_to_decorate: callable):
    cls = method_to_decorate.__class__

    return method_to_decorate
