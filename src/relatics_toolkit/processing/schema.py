SCHEMA = {
    "Element": {
        "R1ElementID": {"not_null": True, "unique": True},
        "R1Element": {"not_null": True, "unique": True},
    },
    "ElementInstances": {
        "R1InstanceID": {"not_null": True, "unique": True},
        "R1Instance": {"not_null": True, "unique": False},
        "R1InstanceDescription": {"not_null": False, "unique": False, "default": None},
        "R1InstanceRichText": {"not_null": False, "unique": False, "default": None},
    },
    "Properties": {
        "Property": {"not_null": True, "unique": True},
    },
    "PropertyInstances": {
        "R1InstanceID": {"not_null": True, "unique": False},
        "Property": {"not_null": True, "unique": False},
        "PropertyInstance": {"not_null": False, "unique": False},
    },
    "Relations": {
        "RelationID": {"not_null": True, "unique": False},
        "Relation": {"not_null": True, "unique": False},
        "Cardinality": {"not_null": False, "unique": False},
        "R1Element": {"not_null": True, "unique": False},
        "R2ElementID": {"not_null": True, "unique": False},
        "R2Element": {"not_null": True, "unique": False},
        "ChildR2ElementID": {"not_null": False, "unique": False, "default": None},
        "ChildR2Element": {"not_null": False, "unique": False, "default": None},
    },
    "RelationInstances": {
        "RelationID": {"not_null": True, "unique": False},
        "Cardinality": {"not_null": False, "unique": False},
        "R1InstanceID": {"not_null": True, "unique": False},
        "R2Element": {"not_null": True, "unique": False},
        "R2InstanceID": {"not_null": True, "unique": False},
        "R2Instance": {"not_null": True, "unique": False},
    },
}
