import cmd
import importlib
import os
from pprint import pprint
import sys

from .lab import Lab

def check_running(func):
    def decorator(self: "LabRunner", *args, **kwargs):
        if not self.lab.running:
            print(f"Error: {self.lab.name} is not running.")
            return
        if self.lab.needs_reconfigure:
            self.lab.start()
        func(self, *args, **kwargs)
    return decorator


class LabRunner(cmd.Cmd):
    lab: Lab
    intro = "Welcome to the lab builder.  Type help or ? to list commands.\n"
    file = None

    def __init__(self, lab: str):
        lab = lab.replace("/", ".").removesuffix(".py")
        # sys.path.append(os.path.join(os.curdir, ".."))
        # importlib.import_module("labs")
        module = importlib.import_module(lab)
        self.lab: Lab = module.lab()
        super().__init__()

    @property
    def prompt(self):
        """Display the command line prompt."""
        return f"{self.lab.name}: "

    def do_start(self, _):
        """Run the `start` command."""
        print("Starting", self.lab.name)
        self.lab.start()

    def do_inspect(self, _):
        """Run the `inspect` command."""
        if self.lab is None:
            self.lab = self.lab()
        pprint(self.lab.inspect(), indent=2)

    def do_stop(self, _):
        """Run the `stop` command."""
        print("Stopping", self.lab.name)
        self.lab.stop()

    def do_exit(self, _):
        """Run the `exit` command."""
        print()
        return True

    def do_EOF(self, arg):
        """Stop the command line."""
        return self.do_exit(arg)
