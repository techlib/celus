import { testSushiUrlReport } from "@/libs/sushi-validation";

let cases = [
  // [URL, ok?]
  ["https://a.b.c/foobar/", true],
  ["https://a.b.c/report/", true],
  ["https://a.b.c/reports/", false],
  ["https://a.b.c/reports", false],
  ["https://reports.b.c/foobar", true],
  ["https://reports.b.c/reports", false],
  ["https://reports.b.c/reports/TR", false],
  ["https://reports.b.c/report/TR", true],
  ["https://a.reports.b.c/foobar", true],
  ["reports/b.c/foobar", true],
];

describe("test SUSHI URL validation", () => {
  test.each(cases)("is URL '%p' ok? %p", (url, ok) => {
    let validation = testSushiUrlReport(url);
    expect(validation).toBe(ok);
  });
});
