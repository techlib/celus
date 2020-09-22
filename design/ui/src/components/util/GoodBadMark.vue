<template>
  <CheckMark
    :true-color="trueColor"
    :false-color="falseColor"
    :true-icon="trueIcon"
    :false-icon="falseIcon"
    :value="value"
    v-bind="$attrs"
  ></CheckMark>
</template>

<script>
import CheckMark from "@/components/util/CheckMark";

export default {
  name: "GoodBadMark",
  components: { CheckMark },

  // this overrides some defaults of properties of CheckMark, others are passed on
  // by binding the $attrs value which contains all non-prop attrs passed to this component
  props: {
    value: { default: false },
    trueColor: { default: "success" },
    falseColor: { default: "error" },
    trueIcon: { default: "fa-check" },
    falseIcon: { default: "fa-times" },
  },
};
</script>

<style scoped></style>
