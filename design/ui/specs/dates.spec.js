import { smartMonthRange } from "@/libs/dates";

let cases = [
  // these test cases are taken from test_flexibledataslicer to ensure the
  // same behavior in backend and frontend
  ["2020-10-01", "2021-03", "2020-10 - 2021-03"],
  ["2020-10-01", "2020-10-01", "2020-10"],
  ["2020-10", "2020-10", "2020-10"],
  ["2020-01-01", "2020-01-01", "2020-01"],
  ["2020-01-01", "2020-12-31", "2020"],
  ["2020-01", "2020-12", "2020"],
  ["2020-01-01", "2020-12-01", "2020-01 - 2020-12"],
  ["2020-01-01", "2021-12-31", "2020 - 2021"],
  ["2020-01", "2021-12", "2020 - 2021"],
];

describe("test SUSHI URL validation", () => {
  test.each(cases)(
    "does output from %p-%p match %p",
    (start, end, expected) => {
      let output = smartMonthRange({ start, end });
      expect(output).toBe(expected);
    }
  );
});
