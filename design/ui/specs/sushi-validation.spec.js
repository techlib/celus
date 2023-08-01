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
  ["https://a.b.c/reports/c5/", true],
  ["https://a.b.c/reports/tr/sub", true],
  ["https://a.b.c/reports/tr/", false],
  ["https://a.b.c/reports/ir_m1/", false],
  ["https://a.b.c/reports/ir/", false],
  ["https://a.b.c/reports/ir_m1", false],
  ["https://a.b.c/reports/ir", false],
  ["https://a.b.c/subpath/reports/c5/", true],
  ["https://a.b.c/subpath/reports/tr/sub", true],
  ["https://a.b.c/subpath/reports/tr/", false],
  ["https://a.b.c/subpath/reports/ir_m1/", false],
  ["https://a.b.c/subpath/reports/ir_m1", false],
  ["https://a.b.c/subpath/reports/ir", false],
  ["https://docuseek2.com/reports/counter5/reports/pr", false], // real-world example
  ["https://docuseek2.com/reports/counter5/", true], // real-world example
  ["https://docuseek2.com/reports/counter5_1/", true],
];

describe("test SUSHI URL validation", () => {
  test.each(cases)("is URL '%p' ok? %p", (url, ok) => {
    let validation = testSushiUrlReport(url);
    expect(validation).toBe(ok);
  });
});
