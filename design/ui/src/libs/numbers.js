import numeral from "numeral";

function formatInteger(integer) {
  if (integer == null) {
    return "-";
  }
  return numeral(integer).format("0,0").replace(/,/g, "\xa0");
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

export { formatInteger, smartFormatFloat };
