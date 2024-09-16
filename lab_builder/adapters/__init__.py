from abc import ABC, abstractmethod
import typing

if typing.TYPE_CHECKING:
    from lab_builder import config
    from lab_builder.lab import Lab, Node


class Adapter(ABC):
    @abstractmethod
    def start(self, lab: "Lab"):
        pass

    @abstractmethod
    def stop(self, lab: "Lab"):
        pass

    @abstractmethod
    def destroy(self, lab: "Lab"):
        pass

    @abstractmethod
    def build(self, lab: "Lab", container_file, tag=None):
        pass

    @abstractmethod
    def exec(self, node: "Node", command: "config.Command"):
        pass
