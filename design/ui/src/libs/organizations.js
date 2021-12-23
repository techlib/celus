function sortOrganizations(organizations, lang) {
  if (!organizations) {
    return [];
  }
  let out = Object.values(organizations);
  if (out.length === 0) return [];
  let loc_name = lang ? `name_${lang}` : "name";
  out.forEach((item) => {
    if (item[loc_name]) {
      item.name = item[loc_name]; // name based on current locale
    } else if (item.name) {
      // item.name should be default language
    } else {
      // other language mutations
      let available = Object.entries(item)
        .filter(([key, value]) => key.startsWith("name_") && !!value)
        .map(([, value]) => value);
      if (available.length > 0) {
        item.name = available[0];
      } else if (item.internal_id) {
        item.name = item.internal_id; // internal_id fallback
      } else if (item.short_name) {
        item.name = item.short_name; // short_name fallback
      } else {
        item.name = "-";
      }
    }
  });
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
