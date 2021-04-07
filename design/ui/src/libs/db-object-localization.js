function itemToString(item, locale = "en") {
  if (item !== null) {
    for (let prefix of ["text_local_", "name_"]) {
      let key = `${prefix}${locale}`;
      if (item[key]) {
        return item[key];
      }
    }
    let result =
      item.name || item.short_name || item.text_local_en || item.text;
    if (result) {
      return result;
    }
    return (
      item.name ?? item.short_name ?? item.text_local_en ?? item.text ?? item
    );
  }
}

export { itemToString };
