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
  let sortBy = [];
  let sortDesc = [];
  if (djangoOrderBy) {
    djangoOrderBy.forEach((item) => {
      if (item.startsWith("-")) {
        sortBy.push(item.substring(1));
        sortDesc.push(true);
      } else {
        sortBy.push(item);
        sortDesc.push(false);
      }
    });
  }
  return { sortBy: sortBy, sortDesc: sortDesc };
}

function dataTableToDjangoOrderBy({ sortBy, sortDesc }) {
  let ret = [];
  if (sortBy) {
    sortBy.forEach((item, index) => {
      let prefix = sortDesc[index] ? "-" : "";
      ret.push(prefix + item);
    });
  }
  return ret;
}

export {
  getNamedObjectSorter,
  localizedNamer,
  djangoToDataTableOrderBy,
  dataTableToDjangoOrderBy,
};
