
import json
import os
import tempfile
from unittest.mock import Mock, PropertyMock, patch
import pytest

from lab_builder.lab import Definition, Lab, Service, deep_merge
from lab_builder.node import HealthCheck, Node


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
        "obj": AttrTestChild(name="test", mylist=["value3"], mydict={"key2": "value3"}),
        "mylist": ["value3", "value", "value1"],
        "mydict": {"key": "value", "key1": "value1", "key2": "value3"},
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
    """Test the name property of a definiton."""
    d = Definition(name="My definition")
    assert d.name == "My definition"

class TestNode(Node):
    """A simple node class for testing."""
    name = "node"
    image = "hello-world"

class TestService(Service):
    """A simple service class for testing."""
    name = "TestService"
    nodes = {
        "test_node": TestNode,
    }

    binds = {
        "test_node": [
            "data1:/data1"
        ]
    }

    ports = {
        "test_node": [
            "8080:8080"
        ]
    }

class TestServiceWithLinks(Service):
    """A simple service class (with node links) for testing."""
    name = "TestService"
    nodes = {
        "test_node1": TestNode,
        "test_node2": TestNode,
        "test_node3": TestNode,
    }

    links = {
        "test_node1": {
            "eth2": "test_node2:eth2",
            "eth3": "test_node3:eth2",
        },
        "test_node2": {
            "eth3": "test_node3:eth3",
        }
    }

class TestLab(Lab):
    """A simple lab class for testing."""
    name = "TestLab"
    services = {
        "test_service": TestService,
    }

    binds = {
        "test_node": [
            "data2:/data2"
        ]
    }


class TestLabWithLinks(Lab):
    """A simple lab class (with links) for testing."""
    name = "TestLab"
    services = {
        "test_service": TestServiceWithLinks,
    }

def test_node_directory():
    """Confirm that the state and definition directories are the expected paths."""
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

def test_node_binds():
    """Confirm that nodes get correct binds."""
    with patch("lab_builder.lab.glob.glob") as glob:
        glob.side_effect = lambda value: [value]
        lab = TestLab()
        node = lab.services["test_service"].nodes["test_node"]
        node_dir = node.state_directory
        lab_dir = lab.state_directory
        service_dir = lab.services["test_service"].state_directory
        want_binds = [
            f"{lab_dir}/data2:/data2:ro",
            f"{service_dir}/data1:/data1:ro",
            f"{node_dir}:/lab_builder_data",
        ]

        assert node.binds == want_binds

def test_node_ports():
    """Confirm ports get passed to the node definition."""
    lab = TestLab()
    node = lab.services["test_service"].nodes["test_node"].as_dict()
    want_ports = ["8080:8080"]
    assert node["ports"] == want_ports

def test_running():
    """The `running` property determines if the complete lab is running.
    
    This test confirms the behavior of the `running` property.
    """
    with (
        patch("lab_builder.lab.Lab.inspect", new_callable=Mock) as inspect,
    ):
        lab = TestLab()
        inspect.return_value = {"containers": []}
        assert lab.running is False

        inspect.return_value = {"containers": [
            {"lab_name": "TestLab", "name": "clab-TestLab-test_node"},
        ]}
        assert lab.running is True

def test_needs_reconfigure():
    """This test confirms the behavior of the `needs_reconfigure` property.

    Labs that may already be running should only be restarted if their topology,
    or other configuration has changed. The `needs_reconfigure` property attempts
    to determine if a reconfiguration is necessary. This test confirms that
    behavior.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        lab = TestLab(base_dir=tmp_dir)
        assert lab.needs_reconfigure is False
        os.makedirs(lab.state_directory)
        with open(lab.topology_file, "w") as topology_file:
            json.dump({}, topology_file)

        assert lab.needs_reconfigure is True

        with open(lab.topology_file, "w") as topology_file:
            topology_file.write(lab.topology_str)

        assert lab.needs_reconfigure is False

def test_links():
    """Confirm the behavior of the link computation."""
    lab = TestLabWithLinks()
    expected_links = [
        {"endpoints": ["test_node1:eth2", "test_node2:eth2"]},
        {"endpoints": ["test_node1:eth3", "test_node3:eth2"]},
        {"endpoints": ["test_node2:eth3", "test_node3:eth3"]},
    ]

    assert expected_links == lab.topology["topology"]["links"]
