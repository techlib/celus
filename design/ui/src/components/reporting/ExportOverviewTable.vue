<i18n lang="yaml" src="@/locales/common.yaml" />
<template>
  <v-data-table :items="exports" item-key="pk" :headers="headers">
    <template #item.output_file="{ item }">
      <a :href="item.output_file" v-if="item.output_file">Data</a>
      <span v-else>-</span>
    </template>
    <template #item.created="{ item }">
      <span v-html="formatDate(item.created)"></span>
    </template>
    <template #item.file_size="{ item }">
      {{ filesize(item.file_size) }}
    </template>
  </v-data-table>
</template>

<script>
import { mapActions } from "vuex";
import axios from "axios";
import { isoDateTimeFormatSpans, parseDateTime } from "@/libs/dates";
import filesize from "filesize";

export default {
  name: "ExportOverviewTable",

  data() {
    return {
      exports: [],
    };
  },

  computed: {
    headers() {
      return [
        { text: this.$t("title_fields.id"), value: "pk", align: "right" },
        {
          text: this.$t("labels.rows"),
          value: "export_params.primary_dimension",
        },
        { text: this.$t("labels.date"), value: "created" },
        { text: this.$t("labels.exported_data"), value: "output_file" },
        {
          text: this.$t("labels.file_size"),
          value: "file_size",
          align: "right",
        },
      ];
    },
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    filesize,
    async fetchData() {
      try {
        let resp = await axios.get("/api/export/flexible-export/");
        this.exports = resp.data;
      } catch (error) {
        this.showSnackbar({
          content: "Could not load the list of exports",
          color: "error",
        });
      }
    },
    formatDate(date) {
      return isoDateTimeFormatSpans(parseDateTime(date));
    },
  },

  mounted() {
    this.fetchData();
  },
};
</script>

<style lang="scss">
span.time {
  font-weight: 300;
  font-size: 87.5%;
}
</style>
