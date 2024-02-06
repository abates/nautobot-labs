
import os
from unittest.mock import Mock, PropertyMock, patch
import pytest
from lab_builder.lab import Definition, Lab, Service
from lab_builder.node import Node


class AttrTest(Definition):
    mylist: list[str]
    mydict: dict[str, str]

class AttrTestParent(Definition):
    mylist: list[str] = ["value"]
    mydict: dict[str, str] = {"key": "value"}

class AttrTestChild(AttrTestParent):
    mylist = ["value1"]
    mydict = {"key1": "value1"}

class AttrTestOverrideChild(AttrTest):
    mydict: list[str]

resolve_attribute_testcases = {
    "No_Inheritance": {
        "obj": AttrTestParent(name="test"),
        "mylist": ["value"],
        "mydict": {"key": "value"},
    },
    "No_Inheritance_with_kwargs": {
        "obj": AttrTestParent(name="test", mylist=["value2"], mydict={"key2": "value2"}),
        "mylist": ["value2", "value"],
        "mydict": {"key": "value", "key2": "value2"},
    },
    "Inheritance": {
        "obj": AttrTestChild(name="test"),
        "mylist": ["value", "value1"],
        "mydict": {"key": "value", "key1": "value1"},
    },
    "Inheritance_with_kwargs": {
        "obj": AttrTestChild(name="test", mylist=["value2"], mydict={"key2": "value2"}),
        "mylist": ["value2", "value", "value1"],
        "mydict": {"key": "value", "key1": "value1", "key2": "value2"},
    },
    "Inheritance_override": {
        "obj": AttrTestOverrideChild(name="test", mylist=["value", "value1"], mydict=["value4", "value5"]),
        "mylist": ["value", "value1"],
        "mydict": ["value4", "value5"],
    }
}

@pytest.mark.parametrize("test_case", resolve_attribute_testcases.values(), ids=resolve_attribute_testcases.keys())
def test_init(test_case):
    obj = test_case.pop("obj")
    for attr_name, want in test_case.items():
        assert getattr(obj, attr_name) == want

DEFINITION_DIR = "/definitions"
STATE_DIR = "/state"

resolve_binds_testcases = {
    "Absolute path to Definition": {
        "binds": [f"{DEFINITION_DIR}/path:/container/destination"],
        "expected": [f"{DEFINITION_DIR}/path:/container/destination:ro"],
    },
    "Absolute path to State": {
        "binds": [f"{STATE_DIR}/path:/container/destination"],
        "expected": [f"{STATE_DIR}/path:/container/destination"],
    },
    "Absolute path to State Read Only": {
        "binds": [f"{STATE_DIR}/path:/container/destination:ro"],
        "expected": [f"{STATE_DIR}/path:/container/destination:ro"],
    },
    "Relative Path": {
        "binds": ["./path:/container/destination"],
        "expected": [f"{DEFINITION_DIR}/path:/container/destination:ro"],
        "globs": [[f"{DEFINITION_DIR}/path"]],
    },
    "Relative Path with Glob": {
        "binds": ["./path/*:/container/destination"],
        "expected": [
            f"{DEFINITION_DIR}/path/1:/container/destination/1:ro",
            f"{DEFINITION_DIR}/path/2:/container/destination/2:ro",
            f"{DEFINITION_DIR}/path/3:/container/destination/3:ro",
        ],
        "globs": [
            [
                f"{DEFINITION_DIR}/path/1",
                f"{DEFINITION_DIR}/path/2",
                f"{DEFINITION_DIR}/path/3",
            ],
        ],
    },
    "Named Path": {
        "binds": ["path:/container/destination"],
        "expected": [f"{STATE_DIR}/path:/container/destination"],
        "globs": [[]],
    },
}

@pytest.mark.parametrize("test_case", resolve_binds_testcases.values(), ids=resolve_binds_testcases.keys())
def test_resolve_binds(test_case):
    layer = Mock()
    type(layer).definition_directory = PropertyMock(return_value=DEFINITION_DIR)
    type(layer).state_directory = PropertyMock(return_value=STATE_DIR)
    definition_import = "lab_builder.lab.Definition"
    with (
        patch(f"{definition_import}.definition_directory", new_callable=PropertyMock) as def_dir,
        patch(f"{definition_import}.state_directory", new_callable=PropertyMock) as state_dir,
        patch("lab_builder.lab.glob.glob") as glob
    ):
        def_dir.return_value = DEFINITION_DIR
        state_dir.return_value = STATE_DIR
        globs = test_case.get("globs", [[bind.split(":")[0]] for bind in test_case["binds"]])
        glob.side_effect = globs
        layer = Definition(name="layer") #, binds={"node": test_case["binds"]})
        received = layer._resolve_binds(test_case["binds"])
        assert test_case["expected"] == received

def test_name():
    d = Definition(name="My definition")
    assert d.name == "My definition"

def test_node_directory():
    class TestNode(Node):
        name = "node"
        image = "hello-world"

    class TestService(Service):
        name = "TestService"
        nodes = {
            "test_node": TestNode,
        }

    class TestLab(Lab):
        name = "TestLab"
        services = {
            "test_service": TestService,
        }

    lab = TestLab()
    base_dir = os.path.dirname(__file__)
    state_dir = os.path.join(os.getcwd(), "TestLab")
    assert lab.state_directory == state_dir
    assert lab.definition_directory == base_dir

    state_dir = os.path.join(state_dir, "test_service")
    assert lab.services["test_service"].state_directory == state_dir
    assert lab.services["test_service"].definition_directory == base_dir

    state_dir = os.path.join(state_dir, "test_node")
    assert lab.services["test_service"].nodes["test_node"].state_directory == state_dir
    assert lab.services["test_service"].nodes["test_node"].definition_directory == base_dir
