<template>
  <v-tooltip bottom v-if="isClamped">
    <template v-slot:activator="{ on }">
      <span v-on="on">{{ clampedText }}&hellip;</span>
    </template>
    {{ text }}
  </v-tooltip>
  <span v-else>{{ text }}</span>
</template>

<script>
export default {
  name: "ShortenText",
  props: {
    text: { required: true, type: String },
    length: { default: 60 },
    tolerance: { default: 3 }, // do not shorten if it would cut this number of letters or less
  },
  data() {
    return {
      clampedText: null,
      isClamped: false,
    };
  },
  methods: {
    recompute() {
      if (this.text.length > this.length + this.tolerance) {
        this.clampedText = this.text.substring(0, this.length);
        this.isClamped = true;
      } else {
        this.clampedText = null;
        this.isClamped = false;
      }
    },
  },
  created() {
    this.recompute();
  },
  watch: {
    length() {
      this.recompute();
    },
    text() {
      this.recompute();
    },
  },
};
</script>

<style scoped></style>
