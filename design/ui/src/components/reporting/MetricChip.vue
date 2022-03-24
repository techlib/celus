<template>
  <v-tooltip bottom max-width="400">
    <template v-slot:activator="{ on }">
      <span v-on="on">
        <v-chip class="ma-1" outlined small>
          <pre>{{ metric.short_name }}</pre>
        </v-chip>
      </span>
    </template>
    <span>{{ metric.name || metric.short_name }}</span>
  </v-tooltip>
</template>

<script>
import { mapState } from "vuex";

export default {
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
