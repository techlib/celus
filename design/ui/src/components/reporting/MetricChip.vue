<template>
  <v-tooltip v-if="metric[`name_${lang}`]" bottom max-width="400">
    <template v-slot:activator="{ on }">
      <span v-on="on">

        <v-chip class="ma-1" outlined small>
          <pre>{{ metric.short_name }}</pre>
        </v-chip>

      </span>
    </template>
    <span>{{ metric[`name_${lang}`] }}</span>
  </v-tooltip>

  <v-chip v-else class="ma-1" outlined small>
    <pre>{{ metric.short_name }}</pre>
  </v-chip>
</template>

<script>
export default {
  props: {
    lang: { required: true, type: String },
    metric: { required: true, type: Object },
  },
};
</script>
