<template>
  <CheckMark
    :true-color="trueColor"
    :false-color="falseColor"
    :true-icon="trueIcon"
    :false-icon="falseIcon"
    v-bind="$attrs"
    :model-value="value"
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
    trueIcon: { default: "fa fa-check" },
    falseIcon: { default: "fa fa-times" },
  },
};
</script>

<style scoped></style>
