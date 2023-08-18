<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<template>
  <span>
    <v-icon small :color="color" class="pr-2">{{ icon }}</v-icon>
    {{ $t("tag_state." + text) }}
  </span>
</template>
<script>
export default {
  name: "TaggingBatchStateWidget",
  props: {
    batch: {},
  },

  computed: {
    text() {
      if (
        this.batch.state === "preflight" &&
        this.batch.preflight?.recognized_columns?.length === 0
      )
        return "no_matched_titles";
      return this.batch.state;
    },
    icon() {
      switch (this.batch.state) {
        case "prefailed":
        case "failed":
          return "fa-exclamation-triangle";
        case "imported":
          return "fa-check";
        case "preflight":
          // no matched titles
          return this.batch.preflight?.recognized_columns?.length === 0
            ? "fa-times"
            : "fa-forward";
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
          // no matched titles
          return this.batch.preflight?.recognized_columns?.length === 0
            ? "error"
            : "warning";
      }
    },
  },
};
</script>
