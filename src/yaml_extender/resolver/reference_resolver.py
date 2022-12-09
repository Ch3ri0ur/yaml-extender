from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from src.yaml_extender.resolver.resolver import Resolver
from src.yaml_extender.xyml_exception import RecursiveReferenceError, ReferenceNotFoundError, ExtYamlSyntaxError

REFERENCE_REGEX = r'\{\{(.+?)(?::(.+?))?\}\}'
ARRAY_REGEX = r'(.*)?\[(\d*)\]'
MAXIMUM_REFERENCE_DEPTH = 30


class ReferenceResolver(Resolver):

    def __init__(self, root_yaml: str | Path, fail_on_resolve: bool = True):
        super().__init__(root_yaml, fail_on_resolve)

    def _Resolver__resolve(self, cur_value: Any, config: dict):
        """Resolves all references in a given value using the provided content dict"""
        new_value = cur_value
        if isinstance(cur_value, dict):
            for k in cur_value.keys():
                cur_value[k] = self._Resolver__resolve(cur_value[k], config)
        elif isinstance(cur_value, list):
            for i, x in enumerate(cur_value):
                cur_value[i] = self._Resolver__resolve(x, config)
        else:
            new_value = self.get_reference(cur_value, config)
        return new_value

    def get_reference(self, value: Any, config: dict, depth: int = 0) -> Any:
        if not isinstance(value, str) or "{" not in value:
            return value
        if depth > 30:
            raise RecursiveReferenceError(value)
        new_value = value
        # In order to store the full match the whole regex is packed into a group
        full_match_regex = f"(?:{REFERENCE_REGEX})"
        ref_match = re.search(full_match_regex, value)
        ref = ref_match.group(1).strip()
        default_value = ref_match.group(2)
        if default_value:
            default_value = default_value.strip()
        failed = ""
        current_config = config
        for subref in ref.split('.'):
            # Resolve arrays
            arr_match = re.match(ARRAY_REGEX, subref)
            if arr_match:
                array_name = arr_match[1]
                try:
                    index = int(arr_match[2])
                except TypeError:
                    raise TypeError(f"Unable to convert index of '{subref}' to integer.")
                if array_name in current_config:
                    if len(current_config[array_name]) > index:
                        current_config = current_config[array_name][index]
                    else:
                        failed = array_name + f"[{index}]"
                        break
                else:
                    failed = array_name
                    break
            else:
                if subref in current_config:
                    current_config = current_config[subref]
                else:
                    failed = subref
                    break
        if failed:
            if default_value:
                ref_val = default_value
            elif self.fail_on_resolve:
                raise ReferenceNotFoundError(failed)
            else:
                ref_val = current_config
        else:
            ref_val = current_config
            # if len(current_config) > 1:
            #     raise ExtYamlSyntaxError(
            #         f"Unable to resolve {value}.The referenced value contains more than 1 element."
            #     )
            # ref_val = list(current_config.values())[0]
        if ref_match.group(0) == value:
            # Reference string is just one reference, therefore the retrieved value can be returned directly
            return ref_val
        else:
            # Replace the reference string with the value
            new_value = new_value.replace(ref_match.group(0), str(ref_val))
            # Resolve consecutive and recursive references
            new_value = self.get_reference(new_value, config, depth + 1)
            return new_value
