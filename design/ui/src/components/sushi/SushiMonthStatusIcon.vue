<template>
  <v-badge color="transparent" :model-value="planned">
    <template #badge>
      <v-icon size="x-small" color="warning"
        >fa fa-arrow-alt-circle-down</v-icon
      >
    </template>
    <v-icon :size="small ? 'small' : 'medium'" :color="statusIcon.color"
      >{{ statusIcon.icon }}
    </v-icon>
  </v-badge>
</template>

<script>
import { dataStateToIcon } from "@/libs/data-state";

export default {
  name: "SushiMonthStatusIcon",
  props: {
    planned: { type: Boolean, default: false },
    status: { type: String },
    small: { type: Boolean },
  },

  computed: {
    statusIcon() {
      return dataStateToIcon(this.status);
    },
  },
};
</script>
