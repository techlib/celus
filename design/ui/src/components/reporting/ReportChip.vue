<template>
  <v-tooltip location="bottom" max-width="400" v-model="show">
    <template v-slot:activator="{ props }">
      <v-chip
        v-bind="props"
        class="ma-1"
        :color="color"
        :variant="!highlight ? 'outlined' : 'flat'"
        label
      >
        <slot> {{ report.short_name }} </slot>
      </v-chip>
    </template>
    <template #default>
      <span>{{ report.short_name }}</span>
      <span v-if="showName && report.name" class="font-weight-light"
        >: {{ report.name }}</span
      >
    </template>
  </v-tooltip>
</template>

<script>
export default {
  name: "ReportChip",

  data() {
    return {
      show: false,
    };
  },

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
