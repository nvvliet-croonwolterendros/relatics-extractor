SCHEMA = {
    "Element": {
        "R1Element": {"required": True},
    },
    "ElementInstances": {
        "R1Instance": {"required": False, "default": None},
        "R1InstanceID": {"required": False, "default": None},
        "R1InstanceDescription": {"required": False, "default": None},
        "R1InstanceRichText": {"required": False, "default": None},
    },
    "Properties": {
        "Property": {"required": False, "default": None},
        "PropertyID": {"required": False, "default": None},
    },
    "PropertyInstances": {
        "R1InstanceID": {"required": False, "default": None},
        "PropertyInstance": {"required": False, "default": None},
        "Property": {"required": False, "default": None},
    },
    "RelationInstances": {
        "R1Instance": {"required": False, "default": None},
        "R1InstanceID": {"required": False, "default": None},
        "R1Element": {"required": False, "default": None},
        "RelationInstanceID": {"required": False, "default": None},
        "RelationID": {"required": False, "default": None},
        "Cardinality": {"required": False, "default": None},
        "R2Instance": {"required": False, "default": None},
        "R2InstanceID": {"required": False, "default": None},
        "R2Element": {"required": False, "default": None},
        "R2ElementID": {"required": False, "default": None},
    },
    "Relations": {
        "Relation": {"required": False, "default": None},
        "RelationID": {"required": False, "default": None},
        "Cardinality": {"required": False, "default": None},
        "R2Element": {"required": False, "default": None},
        "R2ElementID": {"required": False, "default": None},
        "ChildR2Element": {"required": False, "default": None},
        "ChildR2ElementID": {"required": False, "default": None},
    },
}
