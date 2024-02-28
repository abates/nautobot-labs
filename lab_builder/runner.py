"""The lab runner definition."""

import cmd2
import importlib
from pprint import pprint

import platformdirs

from .lab import Lab

def check_running(func):
    """Method decorator that makes sure the lab is already running before continuing to the decorated method."""
    def decorator(self: "LabRunner", *args, **kwargs):
        if not self.lab.running:
            print(f"Error: {self.lab.name} is not running.")
            return
        if self.lab.needs_reconfigure:
            self.lab.start()
        func(self, *args, **kwargs)
    return decorator


class LabRunner(cmd2.Cmd):
    lab: Lab
    intro = "Welcome to the lab builder.  Type help or ? to list commands.\n"
    file = None

    def __init__(self, lab: str):
        lab = lab.replace("/", ".").removesuffix(".py")
        # sys.path.append(os.path.join(os.curdir, ".."))
        # importlib.import_module("labs")
        module = importlib.import_module(lab)
        base_dir = platformdirs.user_data_dir(appname="lab_builder", ensure_exists=True)
        self.lab: Lab = module.lab(base_dir=base_dir)
        super().__init__()

    @property
    def prompt(self):
        """Display the command line prompt."""
        return f"{self.lab.name}: "

    def do_start(self, _):
        """Run the `start` command."""
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

    @check_running
    def do_run(self, statement: cmd2.Statement):
        command, command_args = self.lab.get_command(statement.arg_list)
        command(*command_args)
    
    def complete_run(self, text: str, line: str, begidx: int, endidx: int):
        # The command that is being auto-completed
        command = line[begidx:endidx]

        # remove the `run` portion of the line
        line = line[3:]

        # tokenize the line by spaces
        commands = line.split()

        # if we're autocompleting the last part of the line
        # then the command itself is not the text portion,
        # it is instead the last token
        if line and not line[-1].isspace():
            command = commands.pop()
        return self.lab.complete(commands, command, text)
