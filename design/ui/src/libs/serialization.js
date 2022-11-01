function toBase64JSON(obj) {
  return Buffer.from(JSON.stringify(obj), "utf-8").toString("base64");
}

function toBase64Object(obj) {
  let out = {};
  Object.entries(obj).forEach(([key, value]) => {
    if (typeof value === "object") {
      out[key] = "--" + toBase64JSON(value);
    } else if (typeof value === "string" && value.startsWith("--")) {
      // we need to "escape" strings that start with --, because we use
      // -- to detect if a string is a base64 encoded JSON object
      out[key] = "--" + toBase64JSON(value);
    } else {
      out[key] = value;
    }
  });
  return out;
}

function fromBase64JSON(str) {
  return JSON.parse(Buffer.from(str, "base64").toString("utf-8"));
}

function fromBase64Object(obj) {
  let out = {};
  Object.entries(obj).forEach(([key, value]) => {
    if (typeof value === "string" && value.startsWith("--")) {
      out[key] = fromBase64JSON(value.substring(2));
    } else {
      out[key] = value;
    }
  });
  return out;
}

export { toBase64JSON, toBase64Object, fromBase64Object };
