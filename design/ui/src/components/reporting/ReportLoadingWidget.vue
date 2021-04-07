<template>
  <v-row class="pt-8">
    <v-col cols="12">
      <v-skeleton-loader v-bind="attrs" type="heading" class="pb-4" />
    </v-col>
    <v-col cols="12">
      <v-skeleton-loader v-bind="attrs" type="paragraph" />
    </v-col>
    <v-col :cols="12 / cols.length" v-for="col in cols" :key="col">
      <v-skeleton-loader
        v-bind="attrs"
        type="card-heading, list-item-three-line, list-item-three-line"
        elevation="2"
      />
    </v-col>
    <v-col cols="12">
      <v-skeleton-loader type="paragraph"></v-skeleton-loader>
    </v-col>
  </v-row>
</template>
<script>
export default {
  name: "ReportLoadingWidget",

  props: {
    loading: {},
  },

  data() {
    return {
      cols: [1, 2, 3],
      attrs: {
        loading: true,
      },
    };
  },
};
</script>
