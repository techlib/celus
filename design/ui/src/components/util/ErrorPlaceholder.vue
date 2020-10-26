<template>
  <div
    :style="{
      height: height,
      color: color,
      backgroundColor: bgColor,
      border: `solid 1px ${color}`,
    }"
    class="error-placeholder"
  >
    <div>
      <i class="pb-6" :class="icon"></i>
      <div class="infotext">{{ text }}</div>
    </div>
  </div>
</template>

<script>
import Color from "color";

export default {
  name: "ErrorPlaceholder",

  props: {
    color: {
      default: "orange",
    },
    backgroundColor: {
      default: null,
    },
    text: {
      required: true,
      type: String,
    },
    height: {
      default: "280px",
    },
    icon: {
      default: "fa fa-exclamation-triangle",
    },
  },

  computed: {
    bgColor() {
      return this.backgroundColor || Color(this.color).alpha(0.05);
    },
  },
};
</script>

<style scoped lang="scss">
.error-placeholder {
  font-size: 2rem;
  text-align: center;
  border-radius: 7px;
  display: flex;
  justify-content: center;
  align-items: center;

  div.infotext {
    font-size: 1.75rem;
    font-weight: 300;
  }
}
</style>
