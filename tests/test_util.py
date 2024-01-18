from unittest.mock import patch, Mock

import pytest

from lab_builder.util import resolve_binds

definition_dir = "/definitions"
state_dir = "/state"

resolve_binds_tests = {
    "Absolute path to Definition": {
        "binds": [f"{definition_dir}/path:/container/destination"],
        "expected": [f"{definition_dir}/path:/container/destination:ro"],
    },
    "Absolute path to State": {
        "binds": [f"{state_dir}/path:/container/destination"],
        "expected": [f"{state_dir}/path:/container/destination"],
    },
    "Relative Path": {
        "binds": ["./path:/container/destination"],
        "expected": [f"{definition_dir}/path:/container/destination:ro"],
        "globs": [[f"{definition_dir}/path"]],
    },
    "Relative Path with Glob": {
        "binds": ["./path/*:/container/destination"],
        "expected": [
            f"{definition_dir}/path/1:/container/destination/1:ro",
            f"{definition_dir}/path/2:/container/destination/2:ro",
            f"{definition_dir}/path/3:/container/destination/3:ro",
        ],
        "globs": [
            [
                f"{definition_dir}/path/1",
                f"{definition_dir}/path/2",
                f"{definition_dir}/path/3",
            ],
        ],
    },
    "Named Path": {
        "binds": ["path:/container/destination"],
        "expected": [f"{state_dir}/path:/container/destination"],
        "globs": [[]],
    },

}

@pytest.mark.parametrize("test_case", resolve_binds_tests.values(), ids=resolve_binds_tests.keys())
def test_resolve_binds(test_case):
    layer = Mock()
    layer.definition_directory.return_value = definition_dir
    layer.state_directory.return_value = state_dir
    with patch("lab_builder.util.glob.glob") as glob:
        globs = test_case.get("globs", [[bind.split(":")[0]] for bind in test_case["binds"]])
        glob.side_effect = globs
        got = resolve_binds(layer, test_case["binds"])
        assert test_case["expected"] == got
