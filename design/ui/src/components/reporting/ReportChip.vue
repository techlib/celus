<template>
  <v-tooltip bottom max-width="400">
    <template v-slot:activator="{ on }">
      <span v-on="on">
        <v-chip class="ma-1" :color="color" :outlined="!highlight" label>
          <slot> {{ report.short_name }} </slot>
        </v-chip>
      </span>
    </template>
    <span>{{ report.short_name }}</span>
    <span v-if="showName && report.name" class="font-weight-light"
      >: {{ report.name }}</span
    >
  </v-tooltip>
</template>

<script>
export default {
  name: "ReportChip",

  props: {
    report: {
      required: true,
      type: Object,
    },
    ok: {
      required: false,
      default: true,
      type: Boolean,
    },
    showName: {
      required: false,
      default: true,
      type: Boolean,
    },
    highlight: {
      required: false,
      default: false,
      type: Boolean,
    },
    highlightColor: {
      default: "error",
      type: String,
    },
  },

  computed: {
    color() {
      return this.ok ? "primary" : "secondary";
    },
  },
};
</script>
