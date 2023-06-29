<template>
  <div
    :style="{ height: height, paddingTop: paddingTop }"
    class="loader primary--text"
  >
    <i class="fas fa-spin" :class="iconName"></i>
    <v-progress-linear
      v-if="showProgress"
      :value="progress"
      color="primary"
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
