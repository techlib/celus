<i18n lang="yaml" src="@/locales/common.yaml" />
<i18n lang="yaml" src="@/locales/dialog.yaml" />
<i18n lang="yaml" src="@/locales/reporting.yaml" />

<template>
  <v-container fluid>
    <v-row>
      <v-col>
        <v-data-table
          :items="reports"
          item-key="pk"
          :headers="headers"
          show-expand
          :expanded.sync="expandedRows"
          sort-by="name"
          :loading="loading"
          :search="search"
        >
          <template #top>
            <v-row>
              <v-spacer></v-spacer>
              <v-col cols="auto">
                <v-text-field
                  v-model="search"
                  clearable
                  clear-icon="fa-times"
                  :label="$t('labels.search')"
                  append-icon="fa-search"
                ></v-text-field>
              </v-col>
            </v-row>
          </template>
          <template #item.actions="{ item }">
            <v-tooltip bottom>
              <template #activator="{ on }">
                <v-btn
                  icon
                  color="green lighten-2"
                  @click="runReport(item)"
                  v-on="on"
                >
                  <v-icon small>fa fa-play</v-icon>
                </v-btn>
              </template>
              {{ $t("run_report_tt") }}
            </v-tooltip>

            <v-menu offset-y class="mb-3">
              <template v-slot:activator="menu">
                <v-tooltip bottom>
                  <template #activator="tooltip">
                    <v-btn
                      icon
                      color="blue lighten-2"
                      v-on="{ ...menu.on, ...tooltip.on }"
                    >
                      <v-icon small>fa fa-download</v-icon>
                    </v-btn>
                  </template>
                  {{ $t("export_tt") }}
                </v-tooltip>
              </template>
              <v-list>
                <v-list-item @click="runExport(item, 'xlsx')">
                  <v-list-item-title>{{
                    $t("format.excel")
                  }}</v-list-item-title>
                </v-list-item>
                <v-list-item @click="runExport(item, 'csv')">
                  <v-list-item-title>{{ $t("format.csv") }}</v-list-item-title>
                </v-list-item>
              </v-list>
            </v-menu>

            <v-tooltip bottom>
              <template #activator="{ on }">
                <v-btn
                  icon
                  :to="{ name: 'flexireport', params: { reportId: item.pk } }"
                  v-on="on"
                >
                  <v-icon small>fa fa-eye</v-icon>
                </v-btn>
              </template>
              {{ $t("view_report_tt") }}
            </v-tooltip>

            <v-tooltip bottom>
              <template #activator="{ on }">
                <v-btn
                  icon
                  :to="{
                    name: 'flexireport',
                    params: { reportId: item.pk },
                    query: { edit: true },
                  }"
                  v-on="on"
                  :disabled="!item.canEdit(user, organizations)"
                >
                  <v-icon small>fa fa-edit</v-icon>
                </v-btn>
              </template>
              {{ $t("edit_report_tt") }}
            </v-tooltip>

            <v-tooltip bottom>
              <template #activator="{ on }">
                <v-btn icon v-on="on" @click="startCopy(item)">
                  <v-icon small>far fa-copy</v-icon>
                </v-btn>
              </template>
              {{ $t("copy_report_tt") }}
            </v-tooltip>
            <v-tooltip bottom>
              <template #activator="{ on }">
                <v-btn
                  v-on="on"
                  color="error"
                  icon
                  @click="deleteReport(item.pk)"
                  v-if="item.canEdit(user, organizations)"
                >
                  <v-icon small>fa fa-trash-alt</v-icon>
                </v-btn>
              </template>
              {{ $t("delete_report_tt") }}
            </v-tooltip>

            <span
              v-if="exportHandle && exportHandle.reportId === item.pk"
              class="pl-3"
            >
              <ExportMonitorWidget :export-id="exportHandle.pk" />
            </span>
          </template>

          <template #item.accessLevel="{ item }">
            <span>
              <v-tooltip bottom>
                <template #activator="{ on }">
                  <span v-on="on">
                    <v-icon small>{{ item.accessLevelIcon }}</v-icon>
                  </span>
                </template>
                {{ $t(`access_level_tt.${item.accessLevel}`) }}
              </v-tooltip>
            </span>
          </template>

          <template #item.name="{ item }">
            <v-hover v-slot="{ hover }">
              <div class="d-flex high100">
                <v-edit-dialog
                  @save="saveNewName(item.pk, editedName)"
                  @open="editedName = item.name"
                  v-if="item.canEdit(user, organizations)"
                >
                  {{ item.name }}
                  <template v-slot:input>
                    <v-text-field
                      v-model="editedName"
                      :label="$t('change_name')"
                    ></v-text-field>
                  </template>
                </v-edit-dialog>
                <span v-else>{{ item.name }}</span>
              </div>
            </v-hover>
          </template>

          <template #item.primaryDimension.name="{ item }">
            {{ item.primaryDimension.getName($i18n) }}
            <v-tooltip bottom>
              <template #activator="{ on }">
                <v-icon v-if="item.tagRollUp" x-small v-on="on">fa-tags</v-icon>
              </template>
              {{ $t("tag_roll_up_tt") }}
            </v-tooltip>
          </template>

          <template #item.splitBy.name="{ item }">
            {{ item.splitBy ? item.splitBy.getName($i18n) : "" }}
          </template>

          <template #expanded-item="{ item, headers }">
            <th></th>
            <td :colspan="headers.length - 2" class="py-3">
              <table class="overview text--secondary">
                <tr>
                  <th>{{ $t("labels.report_type") }}:</th>
                  <td>
                    {{ item.reportTypes.map((rt) => rt.name).join(", ") }}
                  </td>
                </tr>
                <tr>
                  <th>{{ $t("title_fields.split_by") }}:</th>
                  <td>
                    {{ item.splitBy?.getName($i18n) }}
                  </td>
                </tr>
                <tr>
                  <th>{{ $t("labels.rows") }}:</th>
                  <td>
                    {{ item.primaryDimension.getName($i18n) }}
                  </td>
                </tr>
                <tr>
                  <th>{{ $t("labels.columns") }}:</th>
                  <td>
                    {{
                      item.groupBy.map((fltr) => fltr.getName($i18n)).join(", ")
                    }}
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
                <tr>
                  <th>{{ $t("labels.settings") }}:</th>
                  <td>
                    <ul class="no-bullets">
                      <li>
                        {{
                          item.includeZeroRows
                            ? $t("show_zero_rows_yes")
                            : $t("show_zero_rows_no")
                        }}
                      </li>
                      <li v-if="item.tagRollUp">{{ $t("tag_roll_up_tt") }}</li>
                      <li v-if="item.showUntaggedRemainder">
                        <v-tooltip bottom>
                          <template #activator="{ on }">
                            <span v-on="on">{{
                              $t("tags_show_remainder")
                            }}</span>
                          </template>
                          {{ $t("tags_show_remainder_tt") }}
                        </v-tooltip>
                      </li>
                    </ul>
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

          <template #body.append="{ headers }">
            <tr>
              <td colspan="1"></td>
              <td :colspan="headers.length - 1">
                <v-btn
                  color="primary"
                  :to="{ name: 'flexitable', query: { wantsSave: true } }"
                >
                  <v-icon small class="mr-2">fa fa-plus</v-icon>
                  {{ $t("add_report") }}
                </v-btn>
              </td>
            </tr>
          </template>
        </v-data-table>
      </v-col>
    </v-row>

    <v-row>
      <v-col>
        <h2 v-if="activeReport" class="text-h5">
          <span>{{ $t("labels.report_output") }}: </span>
          <span class="font-weight-light">{{ activeReport.name }}</span>
        </h2>
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <FlexiTableOutput ref="outputTable" />
      </v-col>
    </v-row>

    <CopyReportDialog
      v-if="copiedReport"
      :report="copiedReport"
      v-model="showCopyDialog"
      @copySuccess="afterCopy"
      @error="copyError"
    />
  </v-container>
</template>

<script>
import { mapActions, mapState } from "vuex";
import axios from "axios";
import { isoDateTimeFormatSpans, parseDateTime } from "@/libs/dates";
import { dimensionMixin } from "@/mixins/dimensions";
import reportTypes from "@/mixins/reportTypes";
import ExportMonitorWidget from "@/components/util/ExportMonitorWidget";
import { FlexiReport } from "@/libs/flexi-reports";
import FlexiTableOutput from "@/components/reporting/FlexiTableOutput";
import CopyReportDialog from "@/components/reporting/CopyReportDialog";

export default {
  name: "StoredReportsTable",

  mixins: [dimensionMixin, reportTypes],

  components: { CopyReportDialog, FlexiTableOutput, ExportMonitorWidget },

  data() {
    return {
      reports: [],
      activeReport: null,
      reportTypes: {},
      expandedRows: [],
      showCopyDialog: false,
      copyDialogTitle: "",
      exportHandle: null,
      editedName: "",
      copiedReport: null,
      loading: false,
      search: "",
    };
  },

  computed: {
    ...mapState(["user", "organizations"]),
    headers() {
      return [
        { text: this.$t("title_fields.access_level"), value: "accessLevel" },
        { text: this.$t("title_fields.name"), value: "name" },
        {
          text: this.$t("title_fields.primary_dimension"),
          value: "primaryDimension.name",
        },
        {
          text: this.$t("title_fields.split_by"),
          value: "splitBy.name",
        },
        {
          text: this.$t("title_fields.actions"),
          value: "actions",
          sortable: false,
        },
      ];
    },
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    async fetchData() {
      this.loading = true;
      try {
        let resp = await axios.get("/api/flexible-report/");
        this.reports = [];
        for (let rt of resp.data) {
          FlexiReport.fromAPIObject(rt, this.reportTypeMap).then((obj) =>
            this.reports.push(obj)
          );
        }
      } catch (error) {
        this.showSnackbar({
          content: "Could not load the list of stored reports",
          color: "error",
        });
      } finally {
        this.loading = false;
      }
    },
    formatDate(date) {
      return isoDateTimeFormatSpans(parseDateTime(date));
    },
    async saveNewName(reportId, value) {
      try {
        let report = this.reports.find((item) => item.pk === reportId);
        if (report) {
          report.rename(value);
        }
      } catch (error) {
        this.showSnackbar({
          content: "Error saving report name: " + error,
          color: "error",
        });
      }
    },
    async runReport(report) {
      this.activeReport = report;
      await this.$refs.outputTable.updateOutput(report);
    },
    async runExport(report, format) {
      let urlParams = {
        ...report.urlParams(),
        format: format,
        name: report.name,
      };
      try {
        let resp = await axios.post("/api/export/flexible-export/", urlParams);
        this.exportHandle = resp.data;
        this.exportHandle.reportId = report.pk;
      } catch (error) {
        this.showSnackbar({
          content: "Could not start export: " + error,
          color: "error",
        });
      }
    },
    async deleteReport(id) {
      let report = this.reports.find((item) => item.pk === id);
      const res = await this.$confirm(
        this.$t("really_delete_report", { title: report.name }),
        {
          title: this.$t("confirm_delete"),
          buttonTrueText: this.$t("delete"),
          buttonFalseText: this.$t("cancel"),
        }
      );
      if (res) {
        try {
          await axios.delete(`/api/flexible-report/${id}`);
          // cleanup
          this.reports = this.reports.filter((item) => item.pk !== id);
          if (this.activeReport && this.activeReport.pk === id) {
            this.activeReport = null;
          }
          this.showSnackbar({
            content: this.$t("delete_report_success"),
            color: "success",
          });
        } catch (error) {
          this.showSnackbar({
            content: "Error deleting report: " + error,
            color: "error",
          });
        }
      }
    },
    startCopy(report) {
      this.copiedReport = report;
      this.showCopyDialog = true;
    },
    afterCopy(report) {
      this.reports.push(report);
      this.showSnackbar({
        content: this.$t("copy_success"),
        color: "success",
      });
      this.copiedReport = null;
      this.showCopyDialog = false;
    },
    copyError(error) {
      this.showSnackbar({
        content: `${this.$t("copy_error")}: ${error}`,
        color: "error",
      });
    },
  },

  async mounted() {
    await this.fetchReportTypes();
    await this.fetchData();
  },
};
</script>

<style lang="scss" scoped>
.invisible {
  visibility: hidden;
}

.high100 {
  padding: 16px 0;
}
</style>
