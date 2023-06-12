<template>
  <v-icon
    x-small
    :color="
      diff > 0 || diff === null ? 'success' : diff === 0 ? 'info' : 'error'
    "
    >fa-arrow-{{
      diff > 0 || diff === null ? "up" : diff === 0 ? "right" : "down"
    }}
  </v-icon>
</template>
<script>
export default {
  name: "TrendArrow",
  props: {
    diff: { required: true },
  },
};
</script>
