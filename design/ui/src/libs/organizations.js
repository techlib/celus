function sortOrganizations(organizations, lang) {
  if (!organizations) {
    return [];
  }
  let out = Object.values(organizations);
  if (out.length === 0) return [];
  let loc_name = lang ? `name_${lang}` : "name";
  out.forEach(
    (item) =>
      (item["name"] = item[loc_name]
        ? item[loc_name]
        : item.name_cs
        ? item.name_cs
        : item.internal_id
        ? item.internal_id
        : item.short_name
        ? item.short_name
        : "-")
  );
  out.sort((a, b) => {
    if ("extra" in a) {
      return -1;
    }
    if ("extra" in b) {
      return 1;
    }
    return a["name"].localeCompare(b["name"]);
  });
  return out;
}

export { sortOrganizations };
