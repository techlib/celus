function serializeException(exception) {
  return Object.entries(exception)
    .map(([key, value]) => `${key}=${value}`)
    .join(";");
}

function serializeArrayOrString(value) {
  if (Array.isArray(value)) {
    return value.join("|");
  } else {
    return value.toString();
  }
}

function serializeObject(object, keyAttr) {
  if (keyAttr in object && "Value" in object) {
    return `${object[keyAttr]}=${serializeArrayOrString(object.Value)}`;
  } else {
    return object.toString();
  }
}

function flattenC51HeaderObject(headerPart) {
  return Object.entries(headerPart)
    .map(([key, value]) => `${key}=${serializeArrayOrString(value)}`)
    .join(";");
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

function flattenC5HeaderObject(headerPart, keyAttr) {
  return Array.isArray(headerPart)
    ? serializeArray(headerPart, keyAttr)
    : headerPart.toString();
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
function counterHeaderRepr(header, counter_version) {
  let release = counter_version || header.Release;
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
      default:
        if (release === "5.1") {
          // "Institution_ID": {
          //   "Proprietary": [
          //     "ProQuest:8421"
          //   ]
          // },
          // {
          //   "Report_Filters": {
          //    "Begin_Date": "2024-10-01",
          //    "End_Date": "2024-10-31"
          //   },
          // }
          res[key] = flattenC51HeaderObject(data);
        } else {
          // "Institution_ID": [
          //    {
          //      "Type": "Proprietary",
          //      "Value": "BRILL:brill-prod_35293"
          //    }
          // ],
          const subkey = key === "Institution_ID" ? "Type" : "Name";
          res[key] = flattenC5HeaderObject(data, subkey);
        }
    }
  }
  return res;
}

export { counterHeaderRepr };
