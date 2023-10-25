function uniqueCounts(arr, key) {
  let out = new Map();
  arr.forEach((item) => {
    let count = out.get(item[key]) || 0;
    out.set(item[key], count + 1);
  });
  return out;
}

export { uniqueCounts };
