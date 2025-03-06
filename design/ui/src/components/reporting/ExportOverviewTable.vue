<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<i18n lang="yaml" src="@/locales/dialog.yaml"></i18n>

<i18n lang="yaml" src="@/locales/reporting.yaml"></i18n>

<template>
  <v-data-table
    :items="exports"
    item-key="pk"
    item-value="pk"
    :headers="headers"
    :loading="loading"
    v-model:expanded="expandedRows"
    v-model:sort-by="orderBy"
    density="default"
  >
    <template #top>
      <v-btn @click="fetchData" color="primary" width="128px">
        <v-icon size="small" class="mr-2">fa fa-sync-alt</v-icon>
        <span v-text="$t('actions.refresh')"></span>
      </v-btn>
    </template>
    <template #[`item.data-table-expand`]="{ item }">
      <v-btn @click="toggleExpand(item)" variant="text" icon size="x-small">
        <v-icon size="small">{{
          expandedRows.includes(item.pk)
            ? "fa fa-angle-down"
            : "fa fa-angle-right"
        }}</v-icon>
      </v-btn>
    </template>
    <template #expanded-row="{ item, columns }">
      <tr class="item_expanded_space">
        <td></td>
        <td :colspan="columns.length - 1" class="py-3">
          <ReportSpecOverview :report="item" :two-panes="twoPanes">
            <template #append>
              <tr v-if="item.status === EXPORT_ERROR">
                <th>{{ $t("error_details") }}:</th>
                <td>{{ item.errorInfo.detail }}</td>
              </tr>
            </template>
          </ReportSpecOverview>
        </td>
      </tr>
    </template>
    <template #[`item.outputFile`]="{ item }">
      <div class="d-inline" width="140px">
        <v-btn
          :href="item.outputFile"
          v-if="item.status === EXPORT_FINISHED"
          variant="text"
          color="primary"
        >
          <v-icon size="small" class="mr-2">fa fa-download</v-icon>
          {{ $t("actions.download") }}
        </v-btn>
        <ExportMonitorWidget
          v-else
          :export-id="item.pk"
          @finished="fetchData"
        ></ExportMonitorWidget>
      </div>
      <v-tooltip location="bottom">
        <template #activator="{ props }">
          <v-btn
            v-bind="props"
            color="error"
            variant="text"
            icon
            @click="deleteExport(item.pk)"
          >
            <v-icon size="x-small">fa fa-trash-alt</v-icon>
          </v-btn>
        </template>
        {{ $t("delete_export_tt") }}
      </v-tooltip>
    </template>
    <template #[`item.created`]="{ item }">
      <span v-html="formatDate(item.created)"></span>
    </template>
    <template #[`item.fileSize`]="{ item }">
      {{ filesize(item.fileSize) }}
    </template>
    <template #[`header.expiresIn`]="{ column }">
      <v-tooltip location="top">
        <template #activator="{ props }">
          <span v-bind="props">{{ column.title }}</span>
        </template>
        <p class="mb-0">{{ $t("expires_in_tt_1") }}</p>
        <p>{{ $t("expires_in_tt_2") }}</p>
      </v-tooltip>
    </template>
    <template #[`item.expiresIn`]="{ item }">
      <span v-html="getExpiration(item.created)"></span>
    </template>
    <template #[`item.primaryDimension`]="{ item }">
      {{ item.primaryDimension.getName($i18n) }}
    </template>
    <template #[`item.statusText`]="{ item }">
      {{ $t("export_status." + item.statusText) }}
    </template>
    <template #[`item.fileFormat`]="{ item }">
      {{ $t(item.fileFormat) }}
    </template>
  </v-data-table>
</template>

<script>
import { mapActions, mapGetters, mapState } from "vuex";
import { formatDistanceToNow } from "date-fns";
import axios from "axios";
import {
  isoDateTimeFormatSpans,
  parseDateTime,
  smartMonthRange,
} from "@/libs/dates";
import { filesize } from "filesize";
import { FlexiExport } from "@/libs/flexi-reports";
import reportTypes from "@/mixins/reportTypes";
import ExportMonitorWidget from "@/components/util/ExportMonitorWidget";
import { EXPORT_ERROR, EXPORT_FINISHED } from "@/libs/flexi-reports";
import translators from "@/mixins/translators";
import ReportSpecOverview from "@/components/reporting/ReportSpecOverview.vue";
import { icon } from "@fortawesome/fontawesome-svg-core";

export default {
  name: "ExportOverviewTable",
  components: { ReportSpecOverview, ExportMonitorWidget },
  mixins: [reportTypes, translators],

  data() {
    return {
      exports: [],
      loading: false,
      expandedRows: [],
      translatedValue: [],
      values: null,
      EXPORT_ERROR,
      EXPORT_FINISHED,
      orderBy: [{ key: "created", order: "desc" }],
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
        {
          title: "",
          value: "data-table-expand",
          sortable: false,
          align: "start",
        },
        { title: this.$t("labels.date"), value: "created", key: "created" },
        { title: this.$t("labels.report_name"), value: "name", key: "name" },
        {
          title: this.$t("labels.rows"),
          value: "primaryDimension",
          key: "primaryDimension",
        },
        {
          title: this.$t("labels.status"),
          value: "statusText",
          key: "statusText",
        },
        {
          title: this.$t("labels.file_size"),
          value: "fileSize",
          key: "fileSize",
          align: "end",
        },
        {
          title: this.$t("labels.file_format"),
          value: "fileFormat",
          key: "fileFormat",
        },
        {
          title: this.$t("labels.exported_data"),
          value: "outputFile",
          sortable: false,
        },
        { title: this.$t("expires_in"), value: "expiresIn", key: "expiresIn" },
      ];
    },
    twoPanes() {
      return this.$vuetify.display.lgAndUp;
    },
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    filesize,
    smartMonthRange,
    expiresOn(createdOn) {
      return new Date(
        parseDateTime(createdOn).getTime() +
          Math.round(this.exportDeletingPeriodInSec) * 1000,
      );
    },
    async fetchData() {
      try {
        let resp = await axios.get("/api/export/flexible-export/");
        this.exports = [];
        for (let exp of resp.data) {
          FlexiExport.fromAPIObject(exp, this.reportTypeMap).then((obj) => {
            this.exports.push(obj);
          });
        }
      } catch (error) {
        this.showSnackbar({
          content: "Could not load the list of exports",
          color: "error",
        });
      }
    },
    toggleExpand(item) {
      const index = this.expandedRows.indexOf(item.pk);
      if (index > -1) {
        this.expandedRows.splice(index, 1);
      } else {
        this.expandedRows.push(item.pk);
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
          color: "warning",
          icon: "fa fa-warning",
        },
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

<style scoped lang="scss">
.filters {
  vertical-align: top;
}

:deep(.v-data-table__tr) {
  &:hover {
    background-color: #00000010;
  }
}
</style>
