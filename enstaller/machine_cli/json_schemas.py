INSTALL_SCHEMA = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "install",
    "description": "machine CLI install args",
    "type": "object",
    "properties": {
        "authentication": {
            "type": "object",
            "oneOf": [
                {"$ref": "#/definitions/simple_authentication"}
            ],
            "description": "Authentication."
        },
        "files_cache": {
            "description": "Where to cache downloaded files.",
            "type": "string"
        },
        "repositories": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of repositories."
        },
        "requirement": {
            "description": "The package requirement",
            "type": "string"
        },
        "store_url": {
            "description": "The url (schema + hostname only of the store to "
                           "connect to).",
            "type": "string"
        }
    },
    "definitions": {
        "simple_authentication": {
            "properties": {
                "kind": {
                    "enum": ["simple"]
                },
                "username": {"type": "string"},
                "password": {"type": "string"}
            },
            "required": ["kind", "username", "password"],
            "additionalProperties": False
        }
    },
    "additionalProperties": False,
    "required": ["authentication", "files_cache", "repositories",
                 "requirement", "store_url"]
}
