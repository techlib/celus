<i18n lang="yaml" src="@/locales/common.yaml" />
<i18n lang="yaml" src="@/locales/dialog.yaml" />
<i18n lang="yaml" src="@/locales/reporting.yaml" />

<template>
  <v-data-table
    :items="exports"
    item-key="pk"
    :headers="headers"
    :loading="loading"
    show-expand
    :expanded.sync="expandedRows"
    :sort-by="['created']"
    :sort-desc="[true]"
  >
    <template #item.outputFile="{ item }">
      <div class="d-inline" width="140px">
        <v-btn
          :href="item.outputFile"
          v-if="item.status === EXPORT_FINISHED"
          text
          color="primary"
        >
          <v-icon small class="mr-2">fa fa-download</v-icon>
          {{ $t("actions.download") }}
        </v-btn>
        <ExportMonitorWidget
          v-else
          :export-id="item.pk"
          @finished="fetchData"
        />
      </div>
      <v-tooltip bottom>
        <template #activator="{ on }">
          <v-btn v-on="on" color="error" icon @click="deleteExport(item.pk)">
            <v-icon small>fa fa-trash-alt</v-icon>
          </v-btn>
        </template>
        {{ $t("delete_export_tt") }}
      </v-tooltip>
    </template>

    <template #item.created="{ item }">
      <span v-html="formatDate(item.created)"></span>
    </template>
    <template #item.fileSize="{ item }">
      {{ filesize(item.fileSize) }}
    </template>

    <template #header.expiresIn="{ header }">
      <v-tooltip top>
        <template #activator="{ on }">
          <span v-on="on">{{ header.text }}</span>
        </template>
        <p class="mb-0">{{ $t("expires_in_tt_1") }}</p>
        <p>{{ $t("expires_in_tt_2") }}</p>
      </v-tooltip>
    </template>
    <template #item.expiresIn="{ item }">
      <span v-html="getExpiration(item.created)"></span>
    </template>

    <template #item.primaryDimension="{ item }">
      {{ item.primaryDimension.getName($i18n) }}
    </template>

    <template #item.statusText="{ item }">
      {{ $t("export_status." + item.statusText) }}
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
        <table class="overview text--secondary">
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
          <tr v-if="item.status === EXPORT_ERROR">
            <th>{{ $t("error_details") }}:</th>
            <td>{{ item.errorInfo.detail }}</td>
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
import { mapActions, mapGetters, mapState } from "vuex";
import { formatDistanceToNow } from "date-fns";
import axios from "axios";
import { isoDateTimeFormatSpans, parseDateTime } from "@/libs/dates";
import filesize from "filesize";
import { FlexiExport } from "@/libs/flexi-reports";
import reportTypes from "@/mixins/reportTypes";
import ExportMonitorWidget from "@/components/util/ExportMonitorWidget";
import { EXPORT_ERROR, EXPORT_FINISHED } from "@/libs/flexi-reports";

export default {
  name: "ExportOverviewTable",
  components: { ExportMonitorWidget },
  mixins: [reportTypes],

  data() {
    return {
      exports: [],
      loading: false,
      expandedRows: [],
      EXPORT_ERROR,
      EXPORT_FINISHED,
    };
  },

  computed: {
    ...mapState({ appLanguage: "appLanguage" }),
    ...mapGetters({
      exportDeletingPeriodInSec: "exportDeletingPeriodInSec",
      dateFnOptions: "dateFnOptions",
    }),
    headers() {
      return [
        { text: this.$t("labels.date"), value: "created" },
        { text: this.$t("labels.report_name"), value: "name" },
        {
          text: this.$t("labels.rows"),
          value: "primaryDimension",
        },
        {
          text: this.$t("labels.status"),
          value: "statusText",
        },
        {
          text: this.$t("labels.file_size"),
          value: "fileSize",
          align: "right",
        },
        {
          text: this.$t("labels.file_format"),
          value: "fileFormat",
        },
        {
          text: this.$t("labels.exported_data"),
          value: "outputFile",
          sortable: false,
        },
        { text: this.$t("expires_in"), value: "expiresIn" },
      ];
    },
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    filesize,
    expiresOn(createdOn) {
      return new Date(
        parseDateTime(createdOn).getTime() +
          Math.round(this.exportDeletingPeriodInSec) * 1000
      );
    },
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
    async deleteExport(pk) {
      let thisExport = this.exports.find((item) => item.pk === pk);
      const res = await this.$confirm(
        this.$t("really_delete_export", {
          title: thisExport.name,
          date: this.formatDate(thisExport.created),
        }),
        {
          title: this.$t("confirm_delete"),
          buttonTrueText: this.$t("delete"),
          buttonFalseText: this.$t("cancel"),
        }
      );
      if (res) {
        try {
          await axios.delete(`/api/export/flexible-export/${pk}`);
          this.fetchData();
          this.showSnackbar({
            content: this.$t("delete_export_success"),
            color: "success",
          });
        } catch (error) {
          this.showSnackbar({
            content: "Error deleting export: " + error,
            color: "error",
          });
        }
      }
    },
    formatDate(date) {
      return isoDateTimeFormatSpans(parseDateTime(date));
    },
    getExpiration(createdOn) {
      return formatDistanceToNow(this.expiresOn(createdOn), this.dateFnOptions);
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
