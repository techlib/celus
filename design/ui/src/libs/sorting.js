function localizedNamer(locale) {
  function namer(obj) {
    return obj[`name_${locale}`] || obj.short_name;
  }
  return namer;
}

function getNamedObjectSorter(locale) {
  function sorter(a, b) {
    let namer = localizedNamer(locale);
    let aName = namer(a);
    let bName = namer(b);
    return aName.localeCompare(bName);
  }
  return sorter;
}

function djangoToDataTableOrderBy(djangoOrderBy) {
  let out = [];
  if (djangoOrderBy) {
    djangoOrderBy.forEach((item) => {
      if (item.startsWith("-")) {
        out.push({ key: item.substring(1), order: "desc" });
      } else {
        out.push({ key: item, order: "asc" });
      }
    });
  }
  return out;
}

export { getNamedObjectSorter, localizedNamer, djangoToDataTableOrderBy };
