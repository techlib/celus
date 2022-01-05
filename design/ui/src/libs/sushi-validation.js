const reportRegexp = new RegExp("/reports($|\\W)");

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

export { testSushiUrlReport };
