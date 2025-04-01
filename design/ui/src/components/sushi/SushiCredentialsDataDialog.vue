<i18n lang="yaml" src="@/locales/dialog.yaml"></i18n>

<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<i18n lang="yaml" src="@/locales/sushi.yaml"></i18n>

<i18n lang="yaml">
en:
  title: Yearly overview
  status:
    no_data: Downloaded, empty data
    failed: An error occurred
    untried: Hasn't been performed yet
    success: Successfully downloaded
  planned: It is already planned to be harvested
  planned_retry: A re-harvest is already planned to make sure there was really no usage
  broken: Broken report type
  selected_count: Number of records to harvest
  selected_count_delete: Number of records to delete
  select_help: You can select unsuccessful records in the table
  select_help_delete: You can select records to delete in the table
  harvest_button: Harvest
  delete_button: Delete
  data_harvest: Harvesting data
  snack_bar:
    credentials_broken: Entire credentials are broken - can't select item for harvesting.
    report_type_broken: Broken report type - can't select item for harvesting.
  delete_mode: Delete mode
  delete_mode_info: activate to delete existing data
  delete_ok: Selected data were deleted.
  mark_failed_as_empty: Mark failed as empty
  mark_failed_as_empty_tt: Selected failed harvests older than two months will be marked as empty data and no further harvesting will be attempted. Useful for cases where the data is known to be empty.
  markable_as_empty: "{count} can be marked as empty | {count} can be marked as empty"
  mark_as_empty_hint: only failed harvests older than two months can be marked as empty

cs:
  title: Yearly overview
  status:
    no_data: Staženo, prázdná data
    failed: Objevila se chyba
    untried: Stahování zatím neproběhlo
    success: Úspěšně staženo
  planned: Stahování bylo naplánováno
  planned_retry: Je naplánováno další stahování, abychom potvrdili neexistenci dat
  broken: Rozbitý report
  selected_count: Počet záznamů ke stáhnutí
  selected_count_delete: Počet záznamů ke smazání
  select_help: Můžete vybrat neúspěšné záznamy z tabulky
  harvest_button: Stáhnout
  delete_button: Smazat
  data_harvest: Stahuji data
  snack_bar:
    credentials_broken: Přístupové údaje jsou rozbité - položku nelze přidat ke stahování.
    report_type_broken: Rozbitý report - položku nelze přidat ke stahování.
  delete_mode: Mazací mód
  delete_mode_info: aktivujte pro mazání dat
  delete_ok: Vybraná data byla smazána.
  mark_failed_as_empty: Označit neúspěšné jako prázdné
  mark_failed_as_empty_tt: Vybraná neúspěšná stahování starší než dva měsíce budou označena jako prázdná a další stahování nebude pokračovat. Užitečné pro případy, kdy je známo, že data jsou prázdná.
  markable_as_empty: "{count} lze označit jako prázdné | {count} lze označit jako prázdné | {count} lze označit jako prázdné"
  mark_as_empty_hint: pouze neúspěšná stahování starší než dva měsíce lze označit jako prázdná
</i18n>

<template>
  <v-card>
    <v-card-title>{{ $t("title") }}</v-card-title>
    <v-card-text class="pb-0">
      <v-container fluid class="pt-0 pb-0">
        <v-row>
          <v-col>
            <SushiCredentialsOverviewHeaderWidget
              v-if="credentials"
              :credentials-name="credentialsName"
              :organization="credentials.organization"
              :platform="credentials.platform"
              :counter-version="credentials.counter_version"
            ></SushiCredentialsOverviewHeaderWidget>
          </v-col>
          <v-col cols="auto" class="align-self-start text-right">
            <v-switch
              :label="$t('delete_mode')"
              v-model="deleteMode"
              color="error"
              density="compact"
              :hint="$t('delete_mode_info')"
              persistent-hint
            ></v-switch>
          </v-col>
        </v-row>
        <v-row>
          <v-col>
            <v-data-table
              :items="processedData"
              :headers="headers"
              :items-per-page-options="itemsPerPageOptions"
              :loading="loadingDownloads"
              @update:options="tableOptions"
              v-model:items-per-page="itemsPerPage"
              :calculate-widths="true"
              v-model="checkedItem"
              v-model:page="page"
              v-model:sort-by="tableOptions.sortBy"
            >
              <template v-slot:item="row">
                <tr>
                  <td
                    v-if="row.index % counterReports.length === 0"
                    :rowspan="counterReports.length"
                  >
                    {{ row.item.year }}
                  </td>
                  <td class="text-center">
                    <v-chip
                      class="mr-1 px-2"
                      :color="row.item['01'].broken ? '#888888' : 'teal'"
                      variant="outlined"
                      label
                    >
                      <SushiReportIndicator
                        :report="row.item.counterReport"
                        :broken-fn="() => row.item['01'].broken"
                      ></SushiReportIndicator>
                    </v-chip>
                  </td>
                  <td v-for="month in months" class="pa-0" :key="month">
                    <v-tooltip location="bottom">
                      <template v-slot:activator="{ props }">
                        <div v-bind="props" class="text-center">
                          <v-btn-toggle
                            v-if="dataReady(row.item, month)"
                            multiple
                            :modelValue="
                              buttonsSelected[row.item.year + '-' + month]
                            "
                            density="comfortable"
                            class="d-block px-1"
                            variant="outlined"
                            color="defaultButton"
                            @update:modelValue="
                              filterBroken(
                                buttonsSelected,
                                credentials,
                                counterReports,
                              ),
                                updateButtonSelection(
                                  $event,
                                  row.item.year + '-' + month,
                                  row.item.counterReport.id,
                                )
                            "
                          >
                            <v-btn
                              :key="`${row.item.year}-${month}-${row.item.counterReport.code}`"
                              :color="buttonColor(row.item[month])"
                              min-height="40px"
                              :value="row.item.counterReport.id"
                              size="small"
                            >
                              <SushiMonthStatusIcon
                                :planned="row.item[month].planned"
                                :status="row.item[month].status"
                              ></SushiMonthStatusIcon>
                            </v-btn>
                          </v-btn-toggle>
                          <span
                            v-else
                            class="text-center d-inline-block pt-3"
                            style="min-height: 40px"
                          >
                            <SushiMonthStatusIcon
                              :planned="row.item[month].planned"
                              :status="row.item[month].status"
                              small
                            ></SushiMonthStatusIcon>
                          </span>
                        </div>
                      </template>
                      <span v-if="row.item[month].status === 'no_data'">{{
                        $t("status.no_data")
                      }}</span>
                      <span v-else-if="row.item[month].status === 'success'">{{
                        $t("status.success")
                      }}</span>
                      <span v-else-if="row.item[month].status === 'failed'">{{
                        $t("status.failed")
                      }}</span>
                      <span v-else-if="row.item[month].status === 'untried'">{{
                        $t("status.untried")
                      }}</span>
                      <span
                        v-else-if="row.item[month].status == 'partial_data'"
                        >{{ $t("sushi.state_desc.partial_data") }}</span
                      >
                      <span v-if="row.item[month].broken"
                        ><br />
                        <v-icon size="small" color="error"
                          >fa fa-exclamation</v-icon
                        >
                        {{ $t("broken") }}</span
                      >
                      <span
                        v-if="
                          row.item[month].planned &&
                          row.item[month].status === 'no_data'
                        "
                        ><br />{{ $t("planned_retry") }}
                      </span>
                      <span v-else-if="row.item[month].planned">
                        <br />{{ $t("planned") }}
                      </span>
                    </v-tooltip>
                  </td>
                </tr>
              </template>
              <template #footer.prepend="">
                <v-btn
                  size="small"
                  color="success"
                  @click="selectAll"
                  class="me-2"
                  >{{ $t("actions.select_all") }}</v-btn
                >
                <v-btn
                  style="margin-right: auto"
                  size="small"
                  color="secondary"
                  @click="unselectAll"
                  >{{ $t("actions.clear_selection") }}</v-btn
                >
              </template>
            </v-data-table>
            <v-dialog max-width="1100px" v-model="showConfirmDeleteDialog">
              <ImportBatchesDeleteConfirm
                v-model="showConfirmDeleteDialog"
                v-if="showConfirmDeleteDialog"
                :import-batch-slices="importBatchSlicesToDelete"
                :intention-slices="intentionSlicesToDelete"
                @cancel="showConfirmDeleteDialog = false"
                @deleted="deletePerformed()"
              ></ImportBatchesDeleteConfirm>
            </v-dialog>
            <v-dialog
              v-model="showHarvestDialog"
              v-if="currentHarvest"
              content-class="top-dialog"
              max-width="1100px"
            >
              <v-card>
                <v-card-text class="pb-0">
                  <v-row>
                    <v-col>
                      <h3 class="pt-3 text-h5">{{ $t("data_harvest") }}</h3>
                    </v-col>
                  </v-row>
                  <v-row>
                    <v-col cols="12" md="6">
                      <SushiCredentialsOverviewHeaderWidget
                        :credentials-name="credentialsName"
                        :organization="credentials.organization"
                        :platform="credentials.platform"
                        :counter-version="credentials.counter_version"
                      ></SushiCredentialsOverviewHeaderWidget>
                    </v-col>
                  </v-row>
                  <div>
                    <SushiFetchIntentionsListWidget
                      :harvest-id="currentHarvest.pk"
                      ref="intentionsList"
                    ></SushiFetchIntentionsListWidget>
                  </div>
                </v-card-text>
                <v-card-actions>
                  <v-spacer></v-spacer>
                  <v-btn
                    @click="
                      showHarvestDialog = false;
                      currentHarvest = null;
                    "
                    class="mb-3 mr-4"
                    variant="elevated"
                    color="defaultButton"
                    >{{ $t("close") }}</v-btn
                  >
                </v-card-actions>
              </v-card>
            </v-dialog>
            <v-dialog
              v-if="showMarkEmptyDialog"
              v-model="showMarkEmptyDialog"
              max-width="640px"
            >
              <div>
                <SushiMarkAsEmptyWidget
                  :records="selectedItemsMarkableAsEmpty"
                  @finished="finishMarkAsEmpty()"
                  @cancel="showMarkEmptyDialog = false"
                  class="pa-3"
                ></SushiMarkAsEmptyWidget>
              </div>
            </v-dialog>
          </v-col>
        </v-row>
        <v-row>
          <v-col>
            <span class="font-weight-black pr-2"
              >{{
                deleteMode ? $t("selected_count_delete") : $t("selected_count")
              }}:</span
            >
            <span>{{ selectedItems.length }}</span>
            <span v-if="selectedItems.length == 0" class="font-italic">
              ({{
                deleteMode ? $t("select_help_delete") : $t("select_help")
              }})</span
            >
            <span v-if="!deleteMode && selectedItems.length > 0">
              ({{ $tc("markable_as_empty", selectedItemsMarkableAsEmpty.length)
              }}<span
                v-if="
                  selectedItems.length > selectedItemsMarkableAsEmpty.length
                "
              >
                - {{ $t("mark_as_empty_hint") }}</span
              >)
            </span>
          </v-col>
        </v-row>
      </v-container>
    </v-card-text>
    <v-card-actions>
      <v-container fluid>
        <v-row no-gutters>
          <v-col cols="auto" v-if="deleteMode">
            <v-btn
              color="error"
              variant="flat"
              elevation="2"
              :disabled="selectedItems.length == 0"
              @click="showConfirmDeleteDialog = true"
            >
              <v-icon size="small" class="mr-2">fas fa-trash</v-icon>
              {{ $t("delete_button") }}
            </v-btn>
          </v-col>
          <v-col cols="auto" v-else>
            <v-btn
              @click="triggerHarvest"
              :disabled="selectedItems.length == 0"
              color="primary"
              class="mr-4"
              variant="flat"
              elevation="2"
            >
              <v-icon size="small" class="mr-2">fa fa-download</v-icon>
              {{ $t("harvest_button") }}
            </v-btn>
            <v-tooltip max-width="600px" location="bottom">
              <template #activator="{ props }">
                <v-btn
                  color="secondary"
                  :disabled="selectedItemsMarkableAsEmpty.length === 0"
                  @click="showMarkEmptyDialog = true"
                  v-bind="props"
                  variant="flat"
                >
                  <v-icon class="mr-2" size="small">fa fa-adjust</v-icon>
                  {{ $t("mark_failed_as_empty") }}
                </v-btn>
              </template>
              <span>{{ $t("mark_failed_as_empty_tt") }}</span>
            </v-tooltip>
          </v-col>
        </v-row>
      </v-container>
      <v-spacer></v-spacer>
      <v-btn
        @click="closeDialog()"
        class="mr-4"
        :right="true"
        variant="flat"
        elevation="2"
        color="defaultButton"
        >{{ $t("close") }}</v-btn
      >
    </v-card-actions>
  </v-card>
</template>

<script>
import axios from "axios";
import { mapActions } from "vuex";
import {
  lastCoveredMonth,
  lastCoveredMonthDate,
  ymFirstDay,
  ymLastDay,
} from "@/libs/dates";
import ImportBatchesDeleteConfirm from "@/components/ImportBatchesDeleteConfirm";
import SushiFetchIntentionsListWidget from "@/components/sushi/SushiFetchIntentionsListWidget";
import SushiCredentialsOverviewHeaderWidget from "@/components/sushi/SushiCredentialsOverviewHeaderWidget";
import SushiReportIndicator from "@/components/sushi/SushiReportIndicator";
import SushiMonthStatusIcon from "@/components/sushi/SushiMonthStatusIcon";
import SushiMarkAsEmptyWidget from "@/components/sushi/SushiMarkAsEmptyWidget.vue";

export default {
  name: "SushiCredentialsDataDialog",
  components: {
    SushiMarkAsEmptyWidget,
    SushiMonthStatusIcon,
    SushiFetchIntentionsListWidget,
    SushiCredentialsOverviewHeaderWidget,
    SushiReportIndicator,
    ImportBatchesDeleteConfirm,
  },
  props: {
    credentials: {
      required: true,
    },
  },
  data() {
    return {
      buttonsSelected: {},
      fetchedData: [],
      loadingDownloads: false,
      page: 1,
      tableOptions: {
        sortBy: [{ key: "year", order: "desc" }],
        sortDesc: [true],
      },
      checkedItem: [],
      currentHarvest: null,
      showHarvestDialog: false,
      showConfirmDeleteDialog: false,
      showMarkEmptyDialog: false,
      deleteMode: false,
    };
  },
  computed: {
    itemsPerPageOptions() {
      return [...Array(5).keys()].map(
        (i) => (i + 1) * this.counterReports.length,
      );
    },
    itemsPerPage() {
      return this.counterReports.length * 2; // 2 years by default
    },
    credentialsDataUrl() {
      if (this.credentials && this.credentials.pk) {
        return `/api/sushi-credentials/${this.credentials.pk}/data/`;
      }
      return null;
    },
    credentialsName() {
      if (this.credentials) {
        return this.credentials.title;
      }
      return null;
    },
    months() {
      let res = [];
      for (let i = 1; i <= 12; i++) {
        res.push(`${i.toString().padStart(2, "0")}`);
      }
      return res;
    },
    processedData() {
      let result = [];
      for (const year_data of this.fetchedData) {
        for (const counterReport of this.counterReports) {
          let record = {
            year: year_data.year,
            counterReport: counterReport,
          };
          for (const month of this.months) {
            for (const row of year_data[month]) {
              if (row.counter_report.code === counterReport.code) {
                const ym = `${year_data.year}-${month}`;
                record[month] = {
                  status: row.status,
                  planned: row.planned,
                  can_harvest:
                    row.can_harvest &&
                    ym >=
                      (this.lastHarvestableMonthMap[counterReport.code] || ""),
                  broken:
                    row.broken ||
                    !!(this.credentials && this.credentials.broken),
                };
              }
            }
          }
          result.push(record);
        }
      }
      return result;
    },
    counterReports() {
      let result = [];
      if (this.fetchedData.length > 0) {
        for (const crt of this.fetchedData[0]["01"]) {
          result.push({
            broken: crt.broken,
            code: crt.counter_report.code,
            id: crt.counter_report.id,
            name: crt.counter_report.name,
            report_type: crt.counter_report.report_type,
          });
        }
      }
      return result;
    },
    counterReportsToReportType() {
      return this.counterReports.reduce(
        (obj, cur) => ({ ...obj, [cur.id]: cur.report_type }),
        {},
      );
    },
    selectedItems() {
      let result = [];
      for (const a in this.buttonsSelected) {
        for (const rt of this.buttonsSelected[a]) {
          let yearMonth = `${a.slice(0, 4)}-${a.slice(5, 7)}`;
          result.push({
            start_date: ymFirstDay(yearMonth),
            end_date: ymLastDay(yearMonth),
            credentials: this.credentials.pk,
            platform: this.credentials.platform.pk,
            organization: this.credentials.organization.pk,
            counter_report: rt,
            report_type: this.counterReportsToReportType[rt],
          });
        }
      }
      return result;
    },
    importBatchSlicesToDelete() {
      return this.selectedItems.map((e) => ({
        platform: e.platform,
        organization: e.organization,
        report_type: e.report_type,
        months: [e.start_date],
      }));
    },
    intentionSlicesToDelete() {
      return this.selectedItems.map((e) => ({
        credentials: this.credentials.pk,
        counter_report: e.counter_report,
        start_date: e.start_date,
      }));
    },
    headers() {
      let res = [
        // {
        //   title: "",
        //   value: "data-table-select",
        //   width: "0",
        //   align: "start",
        // },
        {
          title: this.$t("year"),
          value: "year",
          key: "year",
          class: "wrap",
          align: "start",
        },
        {
          title: this.$t("labels.report_type"),
          value: "counter_report",
          class: "wrap",
          align: "center",
          sortable: false,
        },
      ];
      for (let i = 1; i <= 12; i++) {
        let padded = `${i}`.padStart(2, "0");
        let shortMonthName = new Date(2020, i - 1, 1).toLocaleString(
          this.$i18n.locale,
          { month: "short" },
        );
        res.push({
          title: shortMonthName,
          value: `${padded}`,
          sortable: false,
          align: "center",
          width: 58,
        });
      }
      return res;
    },
    totalCount() {
      return this.processedData.length;
    },
    lastHarvestableMonthMap() {
      return Object.fromEntries(
        this.credentials.counter_reports_long
          .filter((e) => !!e.last_harvestable_month)
          .map((e) => [e.code, e.last_harvestable_month]),
      );
    },
    selectedItemsMarkableAsEmpty() {
      // selected items that are failed and older than one month
      const lastMonth = lastCoveredMonth();
      return this.selectedItems
        .filter((e) => e.start_date <= lastMonth)
        .filter((item) => {
          // find the corresponding record and look at the status
          let year = Number.parseInt(item.start_date.split("-")[0]);
          let month = item.start_date.split("-")[1];
          let cell = this.processedData.find(
            (e) =>
              e.year === year && e.counterReport.id === item.counter_report,
          );
          if (cell) return cell[month].status === "failed";
          return false;
        });
    },
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    updateButtonSelection(newValues, key, value) {
      if (!this.buttonsSelected[key]) {
        this.buttonsSelected[key] = [];
      }
      const existingValues = this.buttonsSelected[key];
      if (newValues.length > 0) {
        this.buttonsSelected[key] = [
          ...new Set([...existingValues, ...newValues]),
        ];
      } else {
        this.buttonsSelected[key] = existingValues.filter(
          (item) => item !== value,
        );
      }
    },
    async loadCredentialsData() {
      if (this.credentialsDataUrl) {
        this.platforms = [];
        this.loadingDownloads = true;
        try {
          let result = await axios.get(this.credentialsDataUrl);
          this.fetchedData = result.data;
        } catch (error) {
          this.showSnackbar({
            content:
              `Error fetching Download data for credentials: ${this.credentials.pk}: ` +
              error,
          });
        } finally {
          this.loadingDownloads = false;
        }
      }
    },
    closeDialog() {
      this.$emit("close");
      this.buttonsSelected = {};
    },
    async triggerHarvest() {
      try {
        let response = await axios.post(`/api/scheduler/harvest/`, {
          intentions: this.selectedItems,
        });
        this.currentHarvest = response.data;
      } catch (error) {
        this.showSnackbar({
          content: "Error starting harvest: " + error,
          color: "error",
        });
      }

      // reload current data
      this.buttonsSelected = {};
      await this.loadCredentialsData();

      this.showHarvestDialog = true;
    },
    isSelectable(record) {
      return this.deleteMode || record.can_harvest;
    },
    dataReady(item, month) {
      let year = parseInt(item.year);
      let month_int = parseInt(month);
      if (!this.isSelectable(item[month]))
        // do not allow re-harvesting of successful downloads
        return false;
      return !this.isFutureDate(year, month_int);
    },
    isFutureDate(year, month) {
      let current = new Date();
      let current_year = current.getFullYear();
      let current_month = current.getMonth() + 1;
      return (
        year > current_year || (year === current_year && month >= current_month)
      );
    },
    buttonColor: (report) => {
      if (report.planned) {
        return "primary lighten-5";
      }
      return "";
    },
    filterBroken(selected, credentials, counterReports) {
      // remove broken credentials
      if (credentials.broken != null) {
        this.showSnackbar({
          content: this.$t("snack_bar.credentials_broken"),
          color: "error",
        });
        // unselect all
        Object.keys(selected).forEach((key) => {
          selected[key] = [];
        });
        return;
      }

      // remove broken report types
      let brokenIds = counterReports.filter((rt) => rt.broken).map((e) => e.id);
      let broken_counter_report = false;
      Object.keys(selected).forEach((key) => {
        let orig_len = selected[key].length;
        selected[key] = selected[key].filter(
          (rt_id) => !brokenIds.includes(rt_id),
        );
        broken_counter_report =
          broken_counter_report || orig_len !== selected[key].length;
      });
      if (broken_counter_report) {
        this.showSnackbar({
          content: this.$t("snack_bar.report_type_broken"),
          color: "error",
        });
      }
    },
    validateSelection() {
      // goes over selected buttons and only keeps the ones compatible with
      // the current mode
      let newSelection = {};
      for (let [yearMonth, trs] of Object.entries(this.buttonsSelected)) {
        let year = parseInt(yearMonth.substring(0, 4));
        let month = yearMonth.substring(5, 7);
        let yearRec = this.fetchedData.find((item) => item.year === year);
        let monthRec = yearRec[month];
        for (let trId of trs) {
          let match = monthRec.find((item) => item.counter_report.id === trId);
          if (this.isSelectable(match)) {
            newSelection[yearMonth] = trs;
          }
        }
      }
      this.buttonsSelected = newSelection;
    },
    deletePerformed() {
      this.showConfirmDeleteDialog = false;
      this.loadCredentialsData();
    },
    selectAll() {
      let pageIdx = this.page - 1;
      let itemsPerPage = this.itemsPerPage;

      if (this.tableOptions.sortBy[0].order === "desc") {
        pageIdx = this.processedData.length - (pageIdx + 1) * itemsPerPage;
        if (pageIdx < 0) pageIdx = 0;
      }
      let end = pageIdx + itemsPerPage;
      let visibleLines = this.processedData.slice(pageIdx, end);
      let bs = {};
      visibleLines.forEach((line) => {
        this.months.forEach((month) => {
          if (this.isFutureDate(line.year, Number.parseInt(month, 10))) return;
          let key = `${line.year}-${month}`;
          if (!bs[key]) {
            bs[key] = [];
          }
          if (
            !bs[key].includes(line.counterReport.id) &&
            this.isSelectable(line[month])
          ) {
            bs[key].push(line.counterReport.id);
          }
        });
      });
      this.buttonsSelected = bs;
    },
    unselectAll() {
      this.buttonsSelected = {};
    },
    finishMarkAsEmpty() {
      this.showMarkEmptyDialog = false;
      this.unselectAll();
      this.loadCredentialsData();
    },
  },

  mounted() {
    this.loadCredentialsData();
  },

  watch: {
    credentialsDataUrl() {
      this.loadCredentialsData();
    },
    showHarvestDialog() {
      if (!this.showHarvestDialog) {
        this.$refs.intentionsList.stop();
        // we need to reload selected credentials in order to update broken state
        this.$emit("reload-credentials");
        this.loadCredentialsData();
      }
    },
    deleteMode() {
      this.validateSelection();
      //this.buttonsSelected = {};
    },
  },
};
</script>

<style scoped lang="scss">
tbody {
  tr:hover {
    background-color: transparent !important;
  }
}
</style>
