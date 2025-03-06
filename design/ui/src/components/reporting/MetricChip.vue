<template>
  <v-tooltip location="bottom" max-width="400" v-model="show">
    <template v-slot:activator="{ props }">
      <v-chip class="ma-1" variant="outlined" size="small" v-bind="props">
        <pre>{{ metric.short_name }}</pre>
      </v-chip>
    </template>
    <span>{{ metric.name || metric.short_name }}</span>
  </v-tooltip>
</template>

<script>
import { mapState } from "vuex";

export default {
  data() {
    return {
      show: false,
    };
  },
  props: {
    metric: { required: true, type: Object },
  },

  computed: {
    ...mapState({
      lang: "appLanguage",
    }),
  },
};
</script>
