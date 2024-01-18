import glob
import inspect
import os


def resolve_binds(layer, binds: list[str]):
    resolved_binds = []
    if binds:
        for bind in binds:
            read_only = ""
            if bind.endswith(":ro"):
                bind = bind[:-3]
                read_only = ":ro"
            local, remote = bind.split(":", 1)
            if not os.path.isabs(local):
                # If the local path starts with a ./ then treat
                # it as a local path, otherwise treat it as a
                # "named" path and put it in the corresponding
                # node directory
                if local.startswith("./"):
                    local = os.path.join(layer.definition_directory(), local[2:])
                    read_only = ":ro"
                else:
                    local = os.path.join(layer.state_directory(), local)
                    # the local path won't match the glob, since this
                    # directory hasn't been created yet, so just add it
                    # and let later handlers create the directory
                    resolved_binds.append(f"{local}:{remote}")
            elif not local.startswith(layer.state_directory()):
                read_only = ":ro"
            
            matches = glob.glob(local)
            if len(matches) == 1 and matches[0] == local:
                resolved_binds.append(f"{local}:{remote}{read_only}")
            else:
                for match in matches:
                    match_remote = os.path.join(remote, os.path.basename(match))
                    resolved_binds.append(f"{match}:{match_remote}{read_only}")
    return resolved_binds

def resolve_attribute(obj, attr_name, values):
    if inspect.isclass(obj):
        cls = obj
    else:
        cls = obj.__class__

    # Copy the values, we don't want to be
    # modifying them and screwing something
    # up elsewhere
    if isinstance(values, dict):
        values = {**values}
    elif isinstance(values, list):
        values = [*values]
    else:
        # Default to wrap values in a list
        values = [values]

    # Reverse the MRO so that we always start
    # from the top most level first. This allows
    # Layers that extend a layer to do overrides
    for _class in reversed(cls.__mro__):
        if hasattr(_class, attr_name):
            if isinstance(values, dict):
                values.update(getattr(_class, attr_name))
            elif isinstance(values, list):
                next_value = getattr(_class, attr_name)
                if isinstance(next_value, list):
                    values.extend(next_value)
                else:
                    values.append(next_value)
                
    return values
