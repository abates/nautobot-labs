

from copy import copy
import os
from typing import Any
import typing


class Field:
    def __init__(self, base_value=None):
        self.base_value = base_value

    def __set_name__(self, owner, name):
        self.public_name = name
        self.private_name = '_' + name

    def _set_default(self, obj):
        setattr(obj, self.private_name, self.base_value)

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        obj.output.append(f"GETTING {self.public_name} from {obj} with {objtype}")

        if not hasattr(obj, self.private_name):
            obj.output.append(f"{obj} does not have {self.private_name}")
            for _class in reversed(obj.__class__.__mro__):
                try:
                    attr = getattr(_class, self.public_name)
                    obj.output.append(f"{_class} has {self.public_name} with {attr}")
                    if isinstance(attr, Field):
                        obj.output.append("and it is a field")
                        attr._set_default(obj)
                    else:
                        setattr(obj, self.public_name, attr)
                except AttributeError:
                    pass

        obj.output.append("GOT HERE!")
        print("\n".join(obj.output))
        return getattr(obj, self.private_name)
        
    def __set__(self, obj, value):
        return setattr(obj, self.private_name, value)


class ListField(Field):
    def _set_default(self, obj):
        base_value = self.base_value or []
        # If the field has already been set from a parent
        # class, then extend it, otherwise set it
        if hasattr(obj, self.private_name):
            getattr(obj, self.private_name).extend(base_value)
        else:
            setattr(obj, self.private_name, [*base_value])
        obj.output.append(f"Set {self.public_name} to default value of {base_value}")

class DictField(Field):
    def _set_default(self, obj):
        base_value = self.base_value or {}
        # If the field has already been set from a parent
        # class, then update it, otherwise set it
        if hasattr(obj, self.private_name):
            getattr(obj, self.private_name).update(base_value)
        else:
            setattr(obj, self.private_name, {**base_value})

class Definition:
    """Definition is a top-level lab configuration/definition class."""

    def __init__(
            self,
            name: str,
            parent: "Definition" = None,
            base_dir: str = None,
            **kwargs,
        ):
        """Initialize a definition.

        Args:
            name (str): Name of the definition. This could be a lab name, service name
                        or node name.
            parent (Definition, optional): The parent definition to which this belongs.
            base_dir (str, optional): The base directory to use for storing state. Defaults to None.

        Raises:
            TypeError: Raise if an unknown keyword argument has been provided.
        """
        self.output = []
        self.name = name
        self.parent = parent
        type_hints = {}
        self.base_dir = base_dir
        if self.base_dir is None:
            self.base_dir = os.getcwd()
        for _class in reversed(self.__class__.__mro__):
            type_hints.update(typing.get_type_hints(_class))

        for attr_name, type_hint in type_hints.items():
            attr_value = kwargs.pop(attr_name, type_hint())
            try:
                attr = getattr(_class, attr_name)
                if isinstance(attr, ListField):
                    setattr(self, attr_name, [*attr_value, *getattr(self, attr_name)])
                elif isinstance(attr, DictField):
                    getattr(self, attr_name).update(attr_value)
                else:
                    setattr(self, attr_name, attr_value)
            except AttributeError:
                # No default value
                setattr(self, attr_name, None)
        keys = list(kwargs.keys())

        if keys:
            raise TypeError(f"{self.__class__.__name__}.__init__() got an unexpected keyword argument '{keys[0]}'")
