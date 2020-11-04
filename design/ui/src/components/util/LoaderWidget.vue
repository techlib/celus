<template>
  <div
    :style="{ height: height, color: color, paddingTop: paddingTop }"
    class="loader"
  >
    <i class="fas fa-spin" :class="iconName"></i>
    <v-progress-linear
      v-if="showProgress"
      :value="progress"
      :color="color"
      class="my-6"
    />
    <p class="text">{{ text }}</p>
  </div>
</template>
<script>
export default {
  name: "LoaderWidget",
  props: {
    loading: {},
    height: { default: "600px" },
    color: { default: "#1db79a88" },
    text: { default: "", required: false },
    iconName: { default: "fa-cog" },
    paddingTop: { default: "160px" },
    showProgress: {
      default: false,
      type: Boolean,
    },
    progress: {
      default: null,
      required: false,
    },
  },
};
</script>
<style scoped lang="scss">
div.loader {
  text-align: center;

  i {
    font-size: 60px;
  }

  p.text {
    margin-top: 1rem;
  }
}
</style>
