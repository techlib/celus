<template>
  <div ref="video" v-resize="updateSize" style="max-width: 800px">
    <iframe
      :width="currentWidth"
      :height="(currentWidth * 9) / 16"
      :src="videoUrl"
    >
    </iframe>
  </div>
</template>

<script>
export default {
  name: "IntroVideo",

  props: {
    videoId: {
      type: String,
      default: "l93wpwv1bs0",
    },
    width: {
      type: Number,
      default: 600,
    },
  },

  data() {
    return {
      currentWidth: this.width,
    };
  },

  computed: {
    videoUrl() {
      return `https://www.youtube.com/embed/${this.videoId}`;
    },
  },

  methods: {
    updateSize() {
      this.currentWidth = this.$refs.video.clientWidth;
    },
  },
};
</script>

<style scoped></style>
