import { describe, expect, test } from "vitest";
import { mount } from "./setup";

import CheckMark from "@/components/util/CheckMark";

describe("CheckMark", () => {
  test("check error icon", () => {
    const wrapper = mount(CheckMark, { props: { modelValue: false } });
    expect(wrapper.html()).toContain("fa-square");
    expect(wrapper.html()).not.toContain("fa-check-square");
  });
  test("check success icon", () => {
    const wrapper = mount(CheckMark, { props: { modelValue: true } });
    expect(wrapper.html()).toContain("fa-check-square");
    expect(wrapper.html()).not.toContain("fa-square");
  });
  test("check error color", () => {
    const wrapper = mount(CheckMark, {
      props: { modelValue: false, trueColor: "green", falseColor: "red" },
    });
    expect(wrapper.html()).toContain("red");
    expect(wrapper.html()).not.toContain("green");
  });
  test("check success color", () => {
    const wrapper = mount(CheckMark, {
      props: { modelValue: true, trueColor: "green", falseColor: "red" },
    });
    expect(wrapper.html()).toContain("green");
    expect(wrapper.html()).not.toContain("red");
  });
});
