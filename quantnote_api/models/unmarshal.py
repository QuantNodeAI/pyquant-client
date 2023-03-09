from typing import Type

from quantnote_api import models

name_to_class = {
    "int": int,
    "float": float,
    "str": str,
}


def unmarshal_json(response_type, resp_json) -> Type[models.AnyDefinition]:
    if response_type in name_to_class.keys():
        return name_to_class[response_type](resp_json)
    if isinstance(resp_json, list):
        if "List[" in response_type:
            response_type = response_type.split("[")[1][:-1]
        return models.Definition._unmarshal_json_list(resp_json, response_type)
    if "Dict[" in response_type:
        known_type = response_type.split(", ")[1][:-1]
        return {k: unmarshal_json(known_type, v) for k, v in resp_json.items()}
    obj = models.name_to_class[response_type]()
    obj.unmarshal_json(resp_json)
    return obj
