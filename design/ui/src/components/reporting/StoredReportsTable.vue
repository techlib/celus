<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<i18n lang="yaml" src="@/locales/dialog.yaml"></i18n>

<i18n lang="yaml" src="@/locales/reporting.yaml"></i18n>

<template>
  <v-container fluid>
    <v-row>
      <v-col>
        <v-data-table
          v-model="selectedRows"
          :items="shownReports"
          item-value="pk"
          :headers="headers"
          v-model:expanded="expandedRows"
          :loading="loading"
          :search="search"
          class="auto-table"
          v-model:sort-by="orderBy"
          filter-mode="union"
          single-select
        >
          <template #top>
            <v-row class="align-center pt-0 my-0">
              <v-col cols="auto">
                <v-checkbox
                  v-model="overrideDates"
                  :label="$t('actions.override_dates')"
                  density="compact"
                  hide-details
                />
              </v-col>
              <v-col cols="auto">
                <v-checkbox
                  v-model="overrideOrganizations"
                  :label="$t('actions.override_organizations')"
                  density="compact"
                  hide-details
                />
              </v-col>
            </v-row>
            <v-row class="align-center pt-0 my-0">
              <v-col cols="auto">
                <v-btn
                  color="primary"
                  :to="{ name: 'flexitable', query: { wantsSave: true } }"
                >
                  <v-icon size="small" class="mr-2">fa fa-plus</v-icon>
                  {{ $t("add_report") }}
                </v-btn>
              </v-col>
              <v-spacer></v-spacer>
              <!-- visibility filter -->
              <v-col cols="6" md="3" lg="3" xl="2">
                <v-select
                  v-model="selectedVisibility"
                  :item-props="itemProps"
                  :items="visibilities"
                  clearable
                  clear-icon="fa fa-times"
                  :label="$t('title_fields.access_level')"
                >
                  <template v-slot:item="{ item, props }">
                    <v-list-item v-bind="props">
                      <v-list-item-title>
                        <v-icon size="small" class="mr-2"
                          >fa-fw {{ accessLevelIcon(item.raw) }}</v-icon
                        >
                        {{ $t(`access_level.${item.raw}`) }}
                      </v-list-item-title>
                    </v-list-item>
                  </template>
                  <template #selection="{ item }">
                    <v-icon size="small" class="mr-2"
                      >fa fa-fw {{ accessLevelIcon(item.raw) }}</v-icon
                    >
                    {{ $t(`access_level.${item.raw}`) }}
                  </template>
                </v-select>
              </v-col>
              <!-- primary dim filter -->
              <v-col cols="6" md="3" lg="3" xl="2">
                <v-select
                  v-model="selectedRowDim"
                  item-title="title"
                  item-value="value"
                  :items="rowDims"
                  clearable
                  clear-icon="fa fa-times"
                  :label="$t('title_fields.primary_dimension')"
                ></v-select>
              </v-col>
              <v-col cols="6" md="3" lg="3" xl="2">
                <v-text-field
                  v-model="search"
                  clearable
                  clear-icon="fa fa-times"
                  :label="$t('labels.search')"
                  append-inner-icon="fa fa-search"
                ></v-text-field>
              </v-col>
            </v-row>
          </template>
          <template #item.actions="{ item }">
            <v-tooltip location="bottom">
              <template #activator="{ props }">
                <v-btn
                  icon
                  density="comfortable"
                  color="green-lighten-2"
                  @click="runReport(item)"
                  v-bind="props"
                  variant="text"
                >
                  <v-icon size="x-small">fa fa-play</v-icon>
                </v-btn>
              </template>
              {{ $t("run_report_tt") }}
            </v-tooltip>
            <v-menu offset-y class="mb-3">
              <template v-slot:activator="{ props: menu }">
                <v-tooltip location="bottom">
                  <template #activator="{ props: tooltip }">
                    <v-btn
                      variant="text"
                      density="comfortable"
                      icon
                      color="blue-lighten-2"
                      v-bind="mergeProps(menu, tooltip)"
                    >
                      <v-icon size="x-small">fa fa-download</v-icon>
                    </v-btn>
                  </template>
                  {{ $t("export_tt") }}
                </v-tooltip>
              </template>
              <v-list>
                <v-list-item @click="runExport(item, 'XLSX')">
                  <v-list-item-title>{{
                    $t("format.excel")
                  }}</v-list-item-title>
                </v-list-item>
                <v-list-item @click="runExport(item, 'XLSX_NO_CHARTS')">
                  <v-list-item-title>{{
                    $t("format.excel_no_charts")
                  }}</v-list-item-title>
                </v-list-item>
                <v-list-item @click="runExport(item, 'ZIP_CSV')">
                  <v-list-item-title>{{ $t("format.csv") }}</v-list-item-title>
                </v-list-item>
              </v-list>
            </v-menu>
            <v-tooltip location="bottom">
              <template #activator="{ props }">
                <v-btn
                  variant="text"
                  density="comfortable"
                  icon
                  :to="{ name: 'flexireport', params: { reportId: item.pk } }"
                  v-bind="props"
                  color="rgba(0, 0, 0, 0.54)"
                >
                  <v-icon size="x-small">fa fa-eye</v-icon>
                </v-btn>
              </template>
              {{ $t("view_report_tt") }}
            </v-tooltip>
            <v-tooltip location="bottom">
              <template #activator="{ props }">
                <v-btn
                  variant="text"
                  density="comfortable"
                  color="rgba(0, 0, 0, 0.54)"
                  icon
                  :to="{
                    name: 'flexireport',
                    params: { reportId: item.pk },
                    query: { edit: true },
                  }"
                  v-bind="props"
                  :disabled="!item.canEdit(user, organizations)"
                >
                  <v-icon size="x-small">fa fa-edit</v-icon>
                </v-btn>
              </template>
              {{ $t("edit_report_tt") }}
            </v-tooltip>
            <v-tooltip location="bottom">
              <template #activator="{ props }">
                <v-btn
                  variant="text"
                  density="comfortable"
                  color="rgba(0, 0, 0, 0.54)"
                  icon
                  v-bind="props"
                  @click="startCopy(item)"
                >
                  <v-icon size="x-small">far fa-copy</v-icon>
                </v-btn>
              </template>
              {{ $t("copy_report_tt") }}
            </v-tooltip>
            <v-tooltip location="bottom">
              <template #activator="{ props }">
                <v-btn
                  v-bind="props"
                  color="red-accent-2"
                  variant="text"
                  density="comfortable"
                  icon
                  @click="deleteReport(item.pk)"
                  v-if="item.canEdit(user, organizations)"
                >
                  <v-icon size="x-small">fa fa-trash-alt</v-icon>
                </v-btn>
              </template>
              {{ $t("delete_report_tt") }}
            </v-tooltip>
            <span
              v-if="exportHandle && exportHandle.reportId === item.pk"
              class="pl-3"
            >
              <ExportMonitorWidget
                :export-id="exportHandle.pk"
              ></ExportMonitorWidget>
            </span>
          </template>
          <template #item.accessLevel="{ item }">
            <span>
              <v-tooltip location="bottom">
                <template #activator="{ props }">
                  <span v-bind="props">
                    <v-icon size="x-small">{{ item.accessLevelIcon }}</v-icon>
                  </span>
                </template>
                {{ $t(`access_level_tt.${item.accessLevel}`) }}
              </v-tooltip>
            </span>
          </template>
          <template #item.name="{ item }">
            <v-menu
              v-if="item.canEdit(user, organizations)"
              :modelValue="activeItem === item"
              offset-y
              @click:outside="closeDialog"
              eager
            >
              <template #activator="{ props: menuProps }">
                <v-hover v-slot="{ isHovering, props: hoverProps }">
                  <span
                    v-bind="{ ...menuProps, ...hoverProps }"
                    @click="openDialog(item)"
                    :style="{ cursor: isHovering ? 'pointer' : '' }"
                  >
                    {{ item.name }}
                  </span>
                </v-hover>
              </template>
              <v-card>
                <v-card-text>
                  <v-text-field
                    v-model="editedName"
                    :label="$t('change_name')"
                    @keyup.enter="saveNewName(item.pk, editedName)"
                    @click.stop
                    :width="editedName.length * 8 + 'px'"
                    min-width="170px"
                    hide-details
                  ></v-text-field>
                </v-card-text>
              </v-card>
            </v-menu>
            <span v-else>{{ item.name }}</span>
            <!-- </div> -->
          </template>
          <template #item.primaryDimension.name="{ item }">
            {{ item.primaryDimension.getName($i18n) }}
            <v-tooltip location="bottom">
              <template #activator="{ props }">
                <v-icon v-if="item.tagRollUp" size="x-small" v-bind="props"
                  >fa fa-tags</v-icon
                >
              </template>
              {{ $t("tag_roll_up_tt") }}
            </v-tooltip>
          </template>
          <template #item.lastUpdated="{ item }">
            <span v-html="isoDateTimeFormatSpans(item.lastUpdated)"></span>
          </template>
          <template v-slot:item.lastUpdatedBy="{ value, item }">
            <v-tooltip location="bottom">
              <template #activator="{ props }">
                <span v-bind="props">
                  {{ userToString(item.lastUpdatedBy) }}
                </span>
              </template>
              <span v-if="!!item.lastUpdatedBy?.first_name">
                <strong>{{ $t("labels.first_name") }}:</strong>
                {{ item.lastUpdatedBy.first_name }}
                <br />
              </span>
              <span v-if="!!item.lastUpdatedBy?.last_name">
                <strong>{{ $t("labels.last_name") }}:</strong>
                {{ item.lastUpdatedBy.last_name }}
                <br />
              </span>
              <span v-if="!!item.lastUpdatedBy?.email">
                <strong>{{ $t("labels.email") }}:</strong>
                {{ item.lastUpdatedBy.email }}
                <br />
              </span>
              <span
                v-if="
                  !!item.lastUpdatedBy?.username &&
                  item.lastUpdatedBy.username != item.lastUpdatedBy?.email
                "
              >
                <strong>{{ $t("labels.username") }}:</strong>
                {{ item.lastUpdatedBy.username }}
                <br />
              </span>
            </v-tooltip>
          </template>
          <template #expanded-row="{ item, columns }">
            <tr class="item_expanded_space">
              <td></td>
              <td :colspan="columns.length - 1" class="py-3">
                <ReportSpecOverview :report="item" :two-panes="twoPanes" />
              </td>
            </tr>
          </template>
          <template #item.data-table-expand="{ item }">
            <v-btn @click="toggleExpand(item)" icon size="small" variant="text">
              <v-icon size="small">
                {{ arrowIcon(item.pk === isSelect[0]) }}-{{
                  expandedRows.includes(item.pk) ? "down" : "right"
                }}
              </v-icon>
            </v-btn>
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
        <FlexiTableOutput ref="outputTable"></FlexiTableOutput>
      </v-col>
    </v-row>
    <CopyReportDialog
      v-if="showCopyDialog && copiedReport"
      :report="copiedReport"
      v-model="showCopyDialog"
      @error="copyError"
      @copySuccess="afterCopy"
    ></CopyReportDialog>
  </v-container>
</template>

<script>
import { mapActions, mapState } from "vuex";
import axios from "axios";
import { isoDateTimeFormatSpans } from "@/libs/dates";
import { dimensionMixin } from "@/mixins/dimensions";
import reportTypes from "@/mixins/reportTypes";
import ExportMonitorWidget from "@/components/util/ExportMonitorWidget";
import { FlexiReport } from "@/libs/flexi-reports";
import { userToString } from "@/libs/user";
import FlexiTableOutput from "@/components/reporting/FlexiTableOutput";
import CopyReportDialog from "@/components/reporting/CopyReportDialog";
import { mergeProps } from "vue";
import translators from "@/mixins/translators";
import ReportSpecOverview from "@/components/reporting/ReportSpecOverview.vue";

export default {
  name: "StoredReportsTable",

  mixins: [dimensionMixin, reportTypes, translators],

  components: {
    ReportSpecOverview,
    CopyReportDialog,
    FlexiTableOutput,
    ExportMonitorWidget,
  },

  data() {
    return {
      report: [],
      possibleValues: [],
      reports: [],
      isSelect: [],
      activeReport: null,
      reportTypes: {},
      expandedRows: [],
      showCopyDialog: false,
      copyDialogTitle: "",
      exportHandle: null,
      editedName: "",
      selectedVisibility: null,
      copiedReport: null,
      loading: false,
      activeItem: null,
      search: "",
      values: null,
      translatedValue: null,
      showNameDialog: false,
      selectedRowDim: null,
      orderBy: [{ key: "name", order: "asc" }],
      selectedRows: [],
      overrideDates: false,
      overrideOrganizations: false,
    };
  },

  computed: {
    ...mapState(["user", "organizations"]),
    rowDims() {
      let out = new Map();
      this.reports.forEach((r) =>
        out.set(r.primaryDimension.ref, r.primaryDimension),
      );
      return Array.from(out).map(([ref, dim]) => ({
        title: dim.getName(this.$i18n),
        value: ref,
      }));
    },
    // name() {
    //   return this.fltr.dimension.getName(this.$i18n);
    // },
    headers() {
      return [
        {
          title: "",
          value: "data-table-expand",
          sortable: false,
          align: "start",
        },
        {
          title: this.$t("title_fields.access_level"),
          value: "accessLevel",
          key: "accessLevel",
        },
        { title: this.$t("title_fields.name"), value: "name", key: "name" },
        {
          title: this.$t("title_fields.primary_dimension"),
          value: "primaryDimension.name",
          key: "primaryDimension.name",
        },
        {
          title: this.$t("title_fields.last_modified"),
          value: "lastUpdated",
        },
        {
          title: this.$t("title_fields.last_modified_by"),
          value: (item) => {
            const user = item.lastUpdatedBy || {};
            return `${user.first_name || ""} ${user.last_name || ""}`.trim();
          },
          key: "lastUpdatedBy",
          filter: (value, search, item) =>
            !search ||
            ["first_name", "last_name", "email", "username"]
              .map((attr) => (item.lastUpdatedBy || {})[attr] || "")
              .some((e) => e.toLowerCase().includes(search.toLowerCase())),
          // key: "splitBy.getName($i18n)",
        },
        {
          title: this.$t("title_fields.actions"),
          value: "actions",
          sortable: false,
        },
      ];
    },
    visibilities() {
      let out = new Set();
      this.reports.forEach((r) => out.add(r.accessLevel));
      return Array.from(out);
    },
    shownReports() {
      let out = this.reports;
      if (this.selectedVisibility) {
        out = out.filter((r) => r.accessLevel === this.selectedVisibility);
      }
      if (this.selectedRowDim) {
        out = out.filter((r) => r.primaryDimension.ref === this.selectedRowDim);
      }
      return out;
    },
    twoPanes() {
      return this.$vuetify.display.lgAndUp;
    },
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
      changeForceHideDateRangeSelector: "changeForceHideDateRangeSelector",
      changeForceHideOrganizationSelector:
        "changeForceHideOrganizationSelector",
    }),
    isoDateTimeFormatSpans,
    userToString,
    openDialog(item) {
      this.activeItem = item;
      this.editedName = item.name;
    },
    closeDialog() {
      this.activeItem = null;
    },
    async fetchData() {
      this.loading = true;
      try {
        let resp = await axios.get("/api/flexible-report/");
        this.reports = [];
        for (let rt of resp.data) {
          FlexiReport.fromAPIObject(rt, this.reportTypeMap).then((obj) =>
            this.reports.push(obj),
          );
        }
        this.values = resp.data;
        if (this.selectedVisibility) {
          this.values = this.values.filter(
            (r) => r.accessLevel === this.selectedVisibility,
          );
        }
        if (this.selectedRowDim) {
          this.values = this.values.filter(
            (r) => r.primaryDimension.ref === this.selectedRowDim,
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
    mergeProps,
    itemProps(item) {
      return {
        title: item.sys,
      };
    },
    accessLevelIcon(level) {
      return FlexiReport.accessLeveLToIcon[level];
    },
    toggleExpand(item) {
      const index = this.expandedRows.indexOf(item.pk);
      if (index > -1) {
        this.expandedRows.splice(index, 1);
      } else {
        this.expandedRows.push(item.pk);
      }
    },
    async saveNewName(reportId, value) {
      try {
        let report = this.reports.find((item) => item.pk === reportId);
        if (report) {
          report.rename(value);
        }
        this.activeItem = null;
      } catch (error) {
        this.showSnackbar({
          content: "Error saving report name: " + error,
          color: "error",
        });
      }
    },
    async runReport(report) {
      this.isSelect = [report.pk];
      this.selectedRows = [report];
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
          color: "warning",
          icon: "fa fa-warning",
        },
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
    async afterCopy(report) {
      this.reports.push(report);
      this.values = [...this.reports];
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
    arrowIcon(isSelected) {
      return isSelected ? "fa fa-angle-double" : "fa fa-angle";
    },
  },

  async mounted() {
    await this.fetchReportTypes();
    await this.fetchData();
  },
  watch: {
    overrideDates: {
      handler() {
        console.log("overrideDates", this.$router.currentRoute.value.name);
        this.changeForceHideDateRangeSelector({
          hide: !this.overrideDates,
          route: this.$router.currentRoute.value.name,
        });
      },
      immediate: true,
    },
    overrideOrganizations: {
      handler() {
        console.log(
          "overrideOrganizations",
          this.$router.currentRoute.value.name,
        );
        this.changeForceHideOrganizationSelector({
          hide: !this.overrideOrganizations,
          route: this.$router.currentRoute.value.name,
        });
      },
      immediate: true,
    },
  },
};
</script>

<style lang="scss" scoped>
.invisible {
  visibility: hidden;
}

:deep(.v-data-table__tr) {
  &:hover {
    background-color: #00000010;
  }
}

:deep(.v-card-text) {
  padding: 5px 12px !important;
}

.subtext {
  font-size: 12px;
}
.overview {
  th {
    color: #00000099;
  }
  td {
    color: #00000099;
  }
}

.list_square {
  list-style-type: square;
}

.second_table_exp {
  vertical-align: top;
  .second_sub_table_exp {
    display: flex;
    flex-direction: column;
    td {
      margin-left: 15px;
    }
  }
}

.high100 {
  padding: 16px 0;
}
</style>
