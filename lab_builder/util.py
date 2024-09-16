
def update_dict(obj, values: dict, attr, key = None, check = lambda value: value):
    if key is None:
        key = attr
    value = getattr(obj, attr, None)
    if check(value):
        if hasattr(value, "as_dict"):
            values[key] = value.as_dict()
        else:
            values[key] = value
