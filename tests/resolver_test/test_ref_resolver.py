import os
from pathlib import Path

import yaml
from unittest.mock import patch

from yaml_extender.resolver.reference_resolver import ReferenceResolver
from yaml_extender.xyml_file import XYmlFile


def test_parse_references():
    val = "this is {{simple}}"
    result = ReferenceResolver.parse_references(val)
    assert result == [["{{simple}}", "simple", None]]
    val = "default is {{ref : default}}"
    result = ReferenceResolver.parse_references(val)
    assert result == [["{{ref : default}}", "ref", "default"]]
    val = "{{ref:}}"
    result = ReferenceResolver.parse_references(val)
    assert result == [["{{ref:}}", "ref", ""]]
    val = "default {{ref:{{ default}}}}"
    result = ReferenceResolver.parse_references(val)
    assert result == [["{{ref:{{ default}}}}", "ref", "{{ default}}"]]
    # Multiple values
    val = "{{ref:{{default}}}} as well as {{ref2:{{default2}}}}"
    result = ReferenceResolver.parse_references(val)
    assert result == [["{{ref:{{default}}}}", "ref", "{{default}}"], ["{{ref2:{{default2}}}}", "ref2", "{{default2}}"]]
    # Test whitespaces
    val = "whitespaces {{ ref: {{default }} }}"
    result = ReferenceResolver.parse_references(val)
    assert result == [["{{ ref: {{default }} }}", "ref", "{{default }}"]]


def test_basic_ref():
    content = yaml.safe_load(
        """
ref_val_1: 123
dict_1:
  subvalue_1: abc
  subvalue_2: "{{ref_val_1}}"
"""
    )
    expected = yaml.safe_load(
        """
ref_val_1: 123
dict_1:
  subvalue_1: abc
  subvalue_2: 123
"""
    )
    ref_resolver = ReferenceResolver()
    result = ref_resolver.resolve(content)

    assert result == expected


def test_recursive_ref():
    content = yaml.safe_load(
        """
ref_val_1: 123
ref_val_2: "{{ref_val_3}}_xyz"
ref_val_3: abc_{{ref_val_1}}
"""
    )
    expected = yaml.safe_load(
        """
ref_val_1: 123
ref_val_2: abc_123_xyz
ref_val_3: abc_123
"""
    )
    ref_resolver = ReferenceResolver()
    result = ref_resolver.resolve(content)

    assert result == expected


def test_dict_ref():
    content = yaml.safe_load(
        """
ref_val_1: "{{dict_1.subvalue_2}}"
dict_1:
  subvalue_1: abc
  subvalue_2: 123
"""
    )
    expected = yaml.safe_load(
        """
ref_val_1: 123
dict_1:
  subvalue_1: abc
  subvalue_2: 123
"""
    )
    ref_resolver = ReferenceResolver()
    result = ref_resolver.resolve(content)

    assert result == expected


def test_array_ref():
    content = yaml.safe_load(
        """
ref_val_1: "{{array_1.1}}"
array_1:
- abc
- xyz
- 123
"""
    )
    expected = yaml.safe_load(
        """
ref_val_1: xyz
array_1:
- abc
- xyz
- 123
"""
    )
    ref_resolver = ReferenceResolver()
    result = ref_resolver.resolve(content)

    assert result == expected


def test_array_in_dict_ref():
    content = yaml.safe_load(
        """
ref_val_1: "{{dict_1.subvalue_2.1.config}}"
dict_1:
  subvalue_1: const_val
  subvalue_2:
  - path: first/path
    config: first.cfg
  - path: second/path
    config: second.cfg
"""
    )
    expected = yaml.safe_load(
        """
ref_val_1: second.cfg
dict_1:
  subvalue_1: const_val
  subvalue_2:
  - path: first/path
    config: first.cfg
  - path: second/path
    config: second.cfg
"""
    )
    ref_resolver = ReferenceResolver()
    result = ref_resolver.resolve(content)

    assert result == expected


def test_basic_default_value():
    content = yaml.safe_load(
        """
ref_val_1: 123
dict_1:
  subvalue_1: abc
  subvalue_2: "{{ref_val_2:default}}"
"""
    )
    expected = yaml.safe_load(
        """
ref_val_1: 123
dict_1:
  subvalue_1: abc
  subvalue_2: default
"""
    )
    ref_resolver = ReferenceResolver()
    result = ref_resolver.resolve(content)

    assert result == expected


def test_nested_default_value():
    content = yaml.safe_load(
        """
    default_value: 123
    config_value: abc
    glob_value: "{{config_value:{{default_value}}}}"
    """
    )
    expected = yaml.safe_load(
        """
    default_value: 123
    config_value: abc
    glob_value: abc
    """
    )
    ref_resolver = ReferenceResolver()
    result = ref_resolver.resolve(content)

    assert result == expected


def test_numeric_default_value():
    content = yaml.safe_load(
        """
ref_val_1: abc
ref_val_2: "{{ not_existing:123 }}"
"""
    )
    expected = yaml.safe_load(
        """
ref_val_1: abc
ref_val_2: 123
"""
    )
    ref_resolver = ReferenceResolver()
    result = ref_resolver.resolve(content)

    assert result == expected


def test_null_default_value():
    content = yaml.safe_load(
        """
ref_val_1: 123
dict_1:
  subvalue_1: abc
  subvalue_2: my_str_{{ref_val_2:}}
"""
    )
    expected = yaml.safe_load(
        """
ref_val_1: 123
dict_1:
  subvalue_1: abc
  subvalue_2: my_str_
"""
    )
    ref_resolver = ReferenceResolver()
    result = ref_resolver.resolve(content)

    assert result == expected


def test_array_default_value():
    content = yaml.safe_load(
        """
ref_val_1: "{{array_1[4]:default}}"
array_1:
- abc
- xyz
- 123
"""
    )
    expected = yaml.safe_load(
        """
ref_val_1: default
array_1:
- abc
- xyz
- 123
"""
    )
    ref_resolver = ReferenceResolver()
    result = ref_resolver.resolve(content)

    assert result == expected


def test_dict_default_value():
    content = yaml.safe_load(
        """
ref_val_1: "{{ dict_1.subvalue_3:default }}"
dict_1:
  subvalue_1: abc
  subvalue_2: 123
"""
    )
    expected = yaml.safe_load(
        """
ref_val_1: default
dict_1:
  subvalue_1: abc
  subvalue_2: 123
"""
    )
    ref_resolver = ReferenceResolver()
    result = ref_resolver.resolve(content)

    assert result == expected


def test_arithmetic_ref():
    content = yaml.safe_load(
        """
value_1: 1
value_2: "{{value_1+1}}"
"""
    )
    expected = yaml.safe_load(
        """
value_1: 1
value_2: 2
"""
    )
    ref_resolver = ReferenceResolver()
    result = ref_resolver.resolve(content)

    assert result == expected

    content = yaml.safe_load(
        """
    value_1: 1
    value_2: string_{{value_1+1}}
    """
    )
    expected = yaml.safe_load(
        """
    value_1: 1
    value_2: string_2
    """
    )
    ref_resolver = ReferenceResolver()
    result = ref_resolver.resolve(content)

    assert result == expected


@patch("yaml_extender.yaml_loader.load")
def test_sub_ref(loader_mock):
    content = yaml.safe_load(
        """
dict_1:
  sub_ref: abc
value_2: "{{ dict_1.sub_ref }}"
"""
    )
    loader_mock.return_value = content
    file = XYmlFile(Path.cwd())
    expected = yaml.safe_load(
        """
dict_1:
  sub_ref: abc
value_2: abc
"""
    )
    assert file.content == expected


@patch("yaml_extender.yaml_loader.load")
def test_env_ref(loader_mock):
    os.environ["TEST_VAL"] = "123"
    content = yaml.safe_load(
        """
value_1: 1
value_2: "{{ xyml.env.TEST_VAL}}"
"""
    )
    loader_mock.return_value = content
    file = XYmlFile(Path.cwd())
    expected = yaml.safe_load(
        """
value_1: 1
value_2: "123"
"""
    )
    assert file.content == expected

    # Test as default value
    content = yaml.safe_load(
        """
    value_1: 1
    value_2: "{{ undefined_value:{{ xyml.env.TEST_VAL}}}}"
    """
    )
    loader_mock.return_value = content
    file = XYmlFile(Path.cwd())
    assert file.content == expected


@patch("yaml_extender.yaml_loader.load")
def test_param_ref(loader_mock):
    content = yaml.safe_load(
        """
    value_1: 1
    value_2: "{{ xyml.param.test_param}}"
    """
    )
    loader_mock.return_value = content
    file = XYmlFile(Path.cwd(), {"test_param": 123})
    expected = yaml.safe_load(
        """
    value_1: 1
    value_2: 123
    """
    )

    assert file.content == expected

    # Test as default value
    content = yaml.safe_load(
        """
    value_1: 1
    value_2: "{{ undefined_value:{{ xyml.param.test_param}}}}"
    """
    )
    loader_mock.return_value = content
    file = XYmlFile(Path.cwd(), {"test_param": 123})
    assert file.content == expected

    @patch("yaml_extender.yaml_loader.load")
    def test_raw_value_ref(loader_mock):
        # Test Lists
        content = yaml.safe_load(
            """
        my_list:
        - a
        - b
        advanced_list:
        - "{{ my_list }}"
        - c
        """
        )
        loader_mock.return_value = content
        file = XYmlFile(Path.cwd())
        expected = yaml.safe_load(
            """
        my_list:
        - a
        - b
        advanced_list:
        - a
        - b
        - c
        """
        )
        assert file.content == expected

    # Test dicts
    content = yaml.safe_load(
        """
    my_dict:
      value_1: a
      value_2: b
    my_list:
    - x
    - y
    advanced_dict:
      my_dict: "{{ my_dict }}"
      my_list: "{{ my_list }}"
    """
    )
    loader_mock.return_value = content
    file = XYmlFile(Path.cwd())
    expected = yaml.safe_load(
        """
    my_dict:
      value_1: a
      value_2: b
    my_list:
    - x
    - y
    advanced_dict:
      my_dict:
        value_1: a
        value_2: b
      my_list:
      - x
      - y
    """
    )
    assert file.content == expected


@patch("yaml_extender.yaml_loader.load")
def test_flat_list_ref(loader_mock):
    # Test Lists
    content = yaml.safe_load(
        """
    my_list:
    - a
    - b
    advanced_list:
    - additional elements {{my_list}}
    - c
    """
    )
    loader_mock.return_value = content
    file = XYmlFile(Path.cwd())
    expected = yaml.safe_load(
        """
    my_list:
    - a
    - b
    advanced_list:
    - additional elements a b
    - c
    """
    )
    assert file.content == expected


@patch("yaml_extender.yaml_loader.load")
def test_dict_list_ref(loader_mock):
    # Test Lists
    content = yaml.safe_load(
        """
    my_dict:
    - first: a
      second: b
    - first: x
      second: y
      third: z
    first: "first = {{my_dict.first}}"
    second: "second = {{my_dict.second}}"
    third: "third = {{my_dict.third}}"
    """
    )
    loader_mock.return_value = content
    file = XYmlFile(Path.cwd())
    expected = yaml.safe_load(
        """
    my_dict:
    - first: a
      second: b
    - first: x
      second: y
      third: z
    first: first = a x
    second: second = b y
    third: third = z
    """
    )
    assert file.content == expected
