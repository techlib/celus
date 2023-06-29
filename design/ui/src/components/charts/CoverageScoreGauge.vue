<template>
  <div style="height: 80px; width: 80px" class="mx-auto">
    <v-progress-circular
      v-if="!loading"
      :value="100 * value"
      size="80"
      width="12"
      rotate="90"
      :color="color"
    >
      <span class="font-weight-bold">{{ shownValue }}</span>
    </v-progress-circular>
    <LargeSpinner v-else />
  </div>
</template>
<script>
import LargeSpinner from "@/components/util/LargeSpinner.vue";

export default {
  name: "CoverageScoreGauge",
  components: { LargeSpinner },
  props: {
    value: {
      type: Number,
      required: false,
    },
    loading: {
      type: Boolean,
      required: false,
    },
  },

  computed: {
    color() {
      // using value^3 pushes the color to the red end of the spectrum
      // which is what we need as we want to highlight the low coverage
      const hue = Math.pow(this.value, 3) * 120;
      return `hsl(${hue}, 100%, 40%)`;
    },
    shownValue() {
      if (this.value === undefined || this.value === null) {
        return "-";
      }
      return Math.round(this.value * 100) + " %";
    },
  },
};
</script>
