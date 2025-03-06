// should match urls that end like this
// /report
// /report/
// /report/tr
// /report/tr/
// /report/ir_m1
// /report/ir_m1/
const reportRegexp = new RegExp(
  "/reports(/*$|/[Tt][Rr]|/[Dd][Rr]|/[Pp][Rr]|/[Ii][Rr])(|_[^/]+){0,1}/{0,1}$",
);

function testSushiUrlReport(url) {
  // returns true if the url is ok, false otherwise
  try {
    let parsed = new URL(url);
    if (parsed) {
      return !reportRegexp.test(parsed.pathname);
    }
    return true;
  } catch (error) {
    // if it is not a valid URL, simply return true - it should fail elsewhere
    return true;
  }
}

// Accepts counter version string and converts it to number (e.g. "5.1" => 51)
function counterVersionToNum(value) {
  return parseInt(value.replace(".", ""));
}

// Accepts counter version number and converts it to string (e.g. 51 => "5.1")
function counterVersionToStr(value) {
  if (value <= 5) {
    return value.toString();
  }
  return (value / 10).toFixed(1);
}

export { testSushiUrlReport, counterVersionToStr, counterVersionToNum };
