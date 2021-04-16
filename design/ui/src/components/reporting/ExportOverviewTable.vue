<i18n lang="yaml" src="@/locales/common.yaml" />
<template>
  <v-data-table
    :items="exports"
    item-key="pk"
    :headers="headers"
    :loading="loading"
    show-expand
    :expanded.sync="expandedRows"
  >
    <template #item.outputFile="{ item }">
      <v-btn
        :href="item.outputFile"
        v-if="item.outputFile"
        text
        color="primary"
        >{{ $t("actions.download") }}</v-btn
      >
      <ExportMonitorWidget v-else :export-id="item.pk" @finished="fetchData" />
    </template>

    <template #item.created="{ item }">
      <span v-html="formatDate(item.created)"></span>
    </template>

    <template #item.fileSize="{ item }">
      {{ filesize(item.fileSize) }}
    </template>

    <template #item.primaryDimension="{ item }">
      {{ item.primaryDimension.getName($i18n) }}
    </template>

    <template #top>
      <v-btn @click="fetchData">
        <v-icon small class="mr-2">fa fa-sync-alt</v-icon>
        <span v-text="$t('actions.refresh')"></span>
      </v-btn>
    </template>

    <template #expanded-item="{ item, headers }">
      <th></th>
      <td :colspan="headers.length - 1" class="py-3">
        <table class="overview">
          <tr>
            <th>{{ $t("labels.report_type") }}:</th>
            <td>
              {{ item.reportTypes.map((rt) => rt.name).join(", ") }}
            </td>
          </tr>
          <tr>
            <th>{{ $t("labels.columns") }}:</th>
            <td>
              {{ item.groupBy.map((fltr) => fltr.getName($i18n)).join(", ") }}
            </td>
          </tr>
          <tr>
            <th>{{ $t("labels.filters") }}:</th>
            <td>
              {{
                item.filters
                  .map((fltr) => fltr.dimension.getName($i18n))
                  .join(", ")
              }}
            </td>
          </tr>
        </table>
      </td>
    </template>

    <template #item.data-table-expand="{ isExpanded, expand }">
      <v-btn @click="expand(!isExpanded)" icon small>
        <v-icon small>{{
          isExpanded ? "fa-angle-down" : "fa-angle-right"
        }}</v-icon>
      </v-btn>
    </template>
  </v-data-table>
</template>

<script>
import { mapActions } from "vuex";
import axios from "axios";
import { isoDateTimeFormatSpans, parseDateTime } from "@/libs/dates";
import filesize from "filesize";
import { FlexiExport } from "@/libs/flexi-reports";
import reportTypes from "@/mixins/reportTypes";
import ExportMonitorWidget from "@/components/util/ExportMonitorWidget";

export default {
  name: "ExportOverviewTable",
  components: { ExportMonitorWidget },
  mixins: [reportTypes],

  data() {
    return {
      exports: [],
      loading: false,
      expandedRows: [],
    };
  },

  computed: {
    headers() {
      return [
        { text: this.$t("labels.date"), value: "created" },
        {
          text: this.$t("labels.rows"),
          value: "primaryDimension",
        },
        {
          text: this.$t("labels.file_size"),
          value: "fileSize",
          align: "right",
        },
        { text: this.$t("labels.exported_data"), value: "outputFile" },
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
        this.exports = [];
        for (let exp of resp.data) {
          FlexiExport.fromAPIObject(exp, this.reportTypeMap).then((obj) =>
            this.exports.push(obj)
          );
        }
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

  async mounted() {
    this.loading = true;
    try {
      await this.fetchReportTypes();
      await this.fetchData();
    } finally {
      this.loading = false;
    }
  },
};
</script>

<style lang="scss">
span.time {
  font-weight: 300;
  font-size: 87.5%;
}

table.overview {
  color: #666666;

  tr {
    margin: 0.75rem 0;

    th {
      text-align: left;
      padding-right: 1rem;
    }
  }
}
</style>
