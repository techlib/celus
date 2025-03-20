def get_or_create_with_map(model, mapping, attr_name, attr_value, other_attrs=None) -> int:
    """
    Given a model, a mapping, an attribute name, an attribute value, and other attributes,
    it returns the primary key of the object in the mapping. If the object is not in the mapping,
    it creates it and adds it to the mapping.
    """

    if attr_value in mapping:
        return mapping[attr_value]["pk"]
    data = {attr_name: attr_value}
    if other_attrs:
        data.update(other_attrs)
    obj, created = model.objects.get_or_create(**data)
    data["pk"] = obj.pk
    mapping[attr_value] = data
    return obj.pk
