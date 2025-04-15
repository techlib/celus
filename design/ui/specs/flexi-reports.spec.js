import { describe, expect, test } from "vitest";

import { FlexiReport } from "@/libs/flexi-reports";
import { ymDateFormat } from "@/libs/dates";

describe("test FlexiReport getSplitOverrideDateRange", () => {
  // try getSplitOverrideDateRange with different date ranges
  test("getSplitOverrideDateRange with 2 months", () => {
    let report = new FlexiReport();
    report.setDateOverride("2021-01-01", "2021-02-28");
    let result = report.getSplitOverrideDateRange();
    expect(ymDateFormat(result.baseStart)).toEqual("2021-01");
    expect(ymDateFormat(result.baseEnd)).toEqual("2021-01");
    expect(ymDateFormat(result.comparedStart)).toEqual("2021-02");
    expect(ymDateFormat(result.comparedEnd)).toEqual("2021-02");
  });
  test("getSplitOverrideDateRange with 3 months - 1 month removed from end", () => {
    let report = new FlexiReport();
    report.setDateOverride("2021-01-01", "2021-03-31");
    let result = report.getSplitOverrideDateRange();
    expect(ymDateFormat(result.baseStart)).toEqual("2021-01");
    expect(ymDateFormat(result.baseEnd)).toEqual("2021-01");
    expect(ymDateFormat(result.comparedStart)).toEqual("2021-02");
    expect(ymDateFormat(result.comparedEnd)).toEqual("2021-02");
  });
  test("getSplitOverrideDateRange with 4 months", () => {
    let report = new FlexiReport();
    report.setDateOverride("2021-01-01", "2021-04-30");
    let result = report.getSplitOverrideDateRange();
    expect(ymDateFormat(result.baseStart)).toEqual("2021-01");
    expect(ymDateFormat(result.baseEnd)).toEqual("2021-02");
    expect(ymDateFormat(result.comparedStart)).toEqual("2021-03");
    expect(ymDateFormat(result.comparedEnd)).toEqual("2021-04");
  });
  test("getSplitOverrideDateRange with 1 month - both dates are the same", () => {
    let report = new FlexiReport();
    report.setDateOverride("2021-01-01", "2021-01-31");
    let result = report.getSplitOverrideDateRange();
    // all values should be the same
    expect(ymDateFormat(result.baseStart)).toEqual("2021-01");
    expect(ymDateFormat(result.baseEnd)).toEqual("2021-01");
    expect(ymDateFormat(result.comparedStart)).toEqual("2021-01");
    expect(ymDateFormat(result.comparedEnd)).toEqual("2021-01");
  });

  test("getSplitOverrideDateRange with 24 months", () => {
    let report = new FlexiReport();
    report.setDateOverride("2021-01-01", "2022-12-31");
    let result = report.getSplitOverrideDateRange();
    expect(ymDateFormat(result.baseStart)).toEqual("2021-01");
    expect(ymDateFormat(result.baseEnd)).toEqual("2021-12");
    expect(ymDateFormat(result.comparedStart)).toEqual("2022-01");
    expect(ymDateFormat(result.comparedEnd)).toEqual("2022-12");
  });
});
