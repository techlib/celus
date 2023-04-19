export default function uniqueMapping(mapping) {
  // mapping is an object with keys and values
  // we want to return a new object with the same keys
  // but with unique values
  // we accomplish this by adding a number to the end of the value
  // if the value is used more than once
  let idToCount = new Map();
  let out = {};
  Object.entries(mapping).forEach(([key, value]) => {
    let count = idToCount.get(value) || 0;
    idToCount.set(value, count + 1);
    out[key] = count ? `${value} #${count + 1}` : value;
  });
  return out;
}
