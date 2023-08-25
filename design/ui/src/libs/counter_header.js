function serializeException(exception) {
  return Object.entries(exception)
    .map(([key, value]) => `${key}=${value}`)
    .join(";");
}

function serializeObject(object, keyAttr) {
  if (keyAttr in object && "Value" in object) {
    return `${object[keyAttr]}=${object.Value}`;
  } else {
    return object.toString();
  }
}

function serializeArray(array, keyAttr) {
  return array
    .map((e) => {
      if (typeof e === "object") {
        return serializeObject(e, keyAttr);
      } else {
        return e.toString();
      }
    })
    .join(";");
}

/**
 * Converts counter header (json) to format which can be shown to user
 *
 * e.g.
 * [ { "Name": "Attributes_To_Show", "Value": "Data_Type|Section_Type" } ]
 * =>
 * Attributes_To_Show=Data_Type|Section_Type|YOP|Access_Type|Access_Method
 *
 */
function counterHeaderRepr(header) {
  let res = {};
  for (const [key, data] of Object.entries(header)) {
    if (typeof data === "string") {
      // Assume that strings are already final
      res[key] = data;
      continue;
    }
    switch (key) {
      case "Exceptions":
        if (typeof data === "object" && Array.isArray(data)) {
          res[key] = data.map((e) => serializeException(e));
        } else {
          res[key] = data.toString();
        }
        break;
      case "Institution_ID":
        res[key] = serializeArray(data, "Type");
        break;
      default:
        res[key] = serializeArray(data, "Name");
    }
  }
  return res;
}

export { counterHeaderRepr };
