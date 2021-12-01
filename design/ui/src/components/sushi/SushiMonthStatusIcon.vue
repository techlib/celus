<template>
  <v-badge :value="planned" color="transparent">
    <template #badge>
      <v-icon x-small color="warning">fa fa-arrow-alt-circle-down</v-icon>
    </template>
    <v-icon small :color="statusIcon.color">{{ statusIcon.icon }} </v-icon>
  </v-badge>
</template>
<script>
import { dataStateToIcon } from "@/libs/data-state";

export default {
  name: "SushiMonthStatusIcon",
  props: {
    planned: { type: Boolean, default: false },
    status: { type: String },
  },

  computed: {
    statusIcon() {
      return dataStateToIcon(this.status);
    },
  },
};
</script>
