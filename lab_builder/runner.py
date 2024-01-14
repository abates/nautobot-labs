import cmd
import importlib

from .lab import Lab

def check_running(func):
    def decorator(self, *args, **kwargs):
        if self.lab is None:
            self.lab = self.lab_class()
            if not self.lab.running:
                print(f"Error: {self.lab_class.name} is not running.")
                return
            self.lab.start()
        func(self, *args, **kwargs)
    return decorator


class LabRunner(cmd.Cmd):
    lab_class: type[Lab]
    lab: Lab
    intro = "Welcome to the lab builder.  Type help or ? to list commands.\n"
    file = None

    def __init__(self, lab: str):
        lab = lab.replace("/", ".").removesuffix(".py")
        module = importlib.import_module(lab)
        self.lab_class: type[Lab] = module.lab
        self.lab: Lab = None
        super().__init__()

    @property
    def prompt(self):
        return f"{self.lab_class.name}: "

    def do_start(self, _):
        print("Starting", self.lab_class.name)
        self.lab = self.lab_class()
        self.lab.start()

    def do_inspect(self, _):
        if self.lab is None:
            self.lab = self.lab_class()
        self.lab.running

    @check_running
    def do_stop(self, _):
        print("Stopping", self.lab_class.name)
        self.lab.stop()

    def do_exit(self, _):
        print()
        return True

    def do_EOF(self, arg):
        return self.do_exit(arg)