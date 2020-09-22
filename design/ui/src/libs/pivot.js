function pivot(data, primary, secondary, count) {
  let result = {};
  let allKeys = new Set();
  for (let rec of data) {
    let key1 = rec[primary];
    let key2 = rec[secondary];
    if (!(key1 in result)) {
      result[key1] = {};
    }
    if (key2 in result[key1]) {
      result[key1][key2] += rec[count];
    } else {
      result[key1][key2] = rec[count];
    }
    allKeys.add(key2);
  }
  let out = [];
  allKeys = [...allKeys].sort();
  for (let [key, value] of Object.entries(result)) {
    let rec = {};
    for (let dimKey of allKeys) {
      if (dimKey in value) {
        rec[dimKey] = value[dimKey];
      } else {
        rec[dimKey] = 0;
      }
    }
    rec[primary] = key;
    out.push(rec);
  }
  return out;
}

export { pivot };
