<template>
  <v-icon small :color="color" class="pr-2">{{ icon }}</v-icon>
</template>
<script>
export default {
  name: "TaggingBatchStateIcon",
  props: {
    batch: {},
  },

  computed: {
    icon() {
      switch (this.batch.state) {
        case "prefailed":
        case "failed":
          return "fa-exclamation-triangle";
        case "imported":
          return "fa-check";
        case "preflight":
          return "fa-forward";
        default:
          return "fa-cogs";
      }
    },
    color() {
      switch (this.batch.state) {
        case "prefailed":
        case "failed":
          return "error";
        case "imported":
          return "success";
        default:
          return "warning";
      }
    },
  },
};
</script>
