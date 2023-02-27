<template>
  <v-progress-linear
    :indeterminate="task.progressPercentage === null"
    :value="task.progressPercentage"
    :height="dense ? '24px' : '32px'"
  >
    <slot></slot>
    <span v-if="task.progressPercentage !== null" class="ps-4">
      {{ progressText }}
      <span v-if="!dense"
        >({{ task.progressCurrent }}/{{ task.progressTotal }})</span
      >
    </span>
  </v-progress-linear>
</template>

<script>
import { round } from "lodash";

export default {
  name: "ServerTaskMonitor",

  props: {
    value: { required: true, type: Object },
    dense: { type: Boolean, default: false },
  },

  data() {
    return {
      task: this.value,
      retryInterval: 2000,
      timeout: null,
    };
  },

  computed: {
    progressText() {
      return this.task.progressPercentage === null
        ? this.task.message
        : `${round(this.task.progressPercentage)} %`;
    },
  },

  methods: {
    async checkProgress() {
      if (this.task) {
        await this.task.getStatus();
        if (this.task.isFinished) {
          this.timeout = null;
          this.$emit("finished", this.task);
        } else {
          this.timeout = setTimeout(this.checkProgress, this.retryInterval);
        }
      }
    },
    stop() {
      if (this.timeout) {
        clearTimeout(this.timeout);
        this.timeout = null;
      }
    },
  },

  mounted() {
    this.checkProgress();
  },

  beforeDestroy() {
    this.stop();
  },
};
</script>

<style scoped></style>
