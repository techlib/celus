import { testSushiUrlReport } from "@/libs/sushi-validation";

let cases = [
  // [URL, ok?]
  ["https://a.b.c/foobar/", true],
  ["https://a.b.c/reports/", true],
  ["https://a.b.c/report/", false],
  ["https://a.b.c/report", false],
  ["https://report.b.c/foobar", true],
  ["https://report.b.c/report", false],
  ["https://report.b.c/report/TR", false],
  ["https://report.b.c/reports/TR", true],
  ["https://a.report.b.c/foobar", true],
  ["report/b.c/foobar", true],
];

describe("test SUSHI URL validation", () => {
  test.each(cases)("is URL '%p' ok? %p", (url, ok) => {
    let validation = testSushiUrlReport(url);
    expect(validation).toBe(ok);
  });
});
