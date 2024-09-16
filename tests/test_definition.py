
from collections import UserList
from dataclasses import dataclass, field
import pytest

from lab_builder import config

class TestConfigList(config.Config, UserList):  # noqa: D101
    def copy(self) -> config.Config:  # noqa: D102
        return TestConfigList(self.data)

    def update(self, other: "TestConfigList"):  # noqa: D102
        self.extend(other.data)

@dataclass
class TestConfig(config.DataclassConfig):  # noqa: D101
    key1: str = None
    key2: str = None
    key3: TestConfigList = field(default_factory=TestConfigList)

node_config_test_cases = {
    "Merge Configs": {
        "input": [
            TestConfig(
                key1="value1"
            ),
            TestConfig(
                key2="value2"
            )
        ],
        "want": TestConfig(
            key1="value1",
            key2="value2",
        )
    },
    "Overwrite Configs":{
        "input": [
            TestConfig(
                key1="value1"
            ),
            TestConfig(
                key1="value2"
            )
        ],
        "want": TestConfig(
            key1="value2",
            key2=None,
        )
    },
     "Don't overwrite with defaults":{
        "input": [
            TestConfig(
                key1="value1",
                key3=TestConfigList(["one", "two", "three"]),
            ),
            TestConfig(
                key1=None
            )
        ],
        "want": TestConfig(
            key1="value1",
            key3=TestConfigList(["one", "two", "three"]),
        )
    },
}

@pytest.mark.parametrize("test_case", node_config_test_cases.values(), ids=node_config_test_cases.keys())
def test_dataclass_config(test_case):
    """Test the dataclass config copy/update mechanism."""
    got = test_case["input"][0].copy()
    for node_config in test_case["input"][1:]:
        got.update(node_config)
    assert test_case["want"] == got


service_config_test_cases = {
    "Merge Configs": {
        "input": [
            config.ServiceConfig(
                node1=config.NodeConfig(image="image1", binds=config.Binds(config.NamedBind(name="test", mount_point="/test"))),
                node2=config.NodeConfig(image="image2"),
            ),
            config.ServiceConfig(
                node1=config.NodeConfig(network_mode="nat"),
                node2=config.NodeConfig(binds=config.Binds(config.NamedBind(name="test1", mount_point="/test1"))),
            ),
        ],
        "want": config.ServiceConfig(
            node1=config.NodeConfig(
                image="image1",
                network_mode="nat",
                binds=config.Binds(config.NamedBind(name="test", mount_point="/test")),
            ),
            node2=config.NodeConfig(
                image="image2",
                binds=config.Binds(config.NamedBind(name="test1", mount_point="/test1")),
            ),
        ),
    },
}

@pytest.mark.parametrize("test_case", service_config_test_cases.values(), ids=service_config_test_cases.keys())
def test_service_config(test_case):
    """Test the dataclass config copy/update mechanism."""
    got = test_case["input"][0].copy()
    for node_config in test_case["input"][1:]:
        got.update(node_config)
    assert set(test_case["want"].node_names) == set(got.node_names)
    for node_name in test_case["want"].node_names:
        assert getattr(test_case["want"], node_name) == getattr(got, node_name)

def test_invalid_service_config():
    got_error = False
    try:
        config.ServiceConfig(
            node1="node1",
        )
    except ValueError:
        got_error = True
    assert got_error
