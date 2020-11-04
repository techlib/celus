import numeral from "numeral";

function formatInteger(integer, empty = "-") {
  if (integer == null) {
    return empty;
  }
  return numeral(integer).format("0,0").replace(/,/g, "\xa0");
}

function padIntegerWithZeros(integer, format = "00") {
  return numeral(integer).format(format);
}

function smartFormatFloat(number, digits = 3) {
  if (number == null) {
    return "-";
  }
  // shows 3 valid decimals and at least one number after decimal point
  const intpart = numeral(number).format("0");
  let decimalPoints = digits - intpart.length;
  if (intpart === "0") decimalPoints += 1;
  if (decimalPoints <= 0) decimalPoints = 1;
  let decPart = "";
  if (decimalPoints) {
    decPart = ".";
    for (let i = 0; i < decimalPoints; i++) {
      decPart += "0";
    }
  }
  return numeral(number)
    .format("0,0" + decPart)
    .replace(/,/g, "\xa0");
}

function formatFloat(number, decimalPlaces = 3) {
  if (number === null) {
    return "-";
  }
  let decPart = "";
  for (let i = 0; i < decimalPlaces; i++) {
    decPart += "0";
  }
  return numeral(number)
    .format("0,0." + decPart)
    .replace(/,/g, "\xa0");
}

export { formatInteger, padIntegerWithZeros, smartFormatFloat, formatFloat };
