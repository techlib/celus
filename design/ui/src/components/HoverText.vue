<template>
  <div>
    <span v-on:mouseenter="on" @mouseleave="off">
      <slot></slot>
    </span>
    <span :class="{ hidden: !isOn }">
      <slot name="hover"></slot>
    </span>
  </div>
</template>

<script>
export default {
  name: "HoverText",

  data() {
    return {
      isOn: false,
    };
  },

  methods: {
    on() {
      this.isOn = true;
    },

    off() {
      this.isOn = false;
    },
  },
};
</script>

<style scoped>
.hidden {
  display: none;
}
</style>
