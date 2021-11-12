<i18n lang="yaml" src="@/locales/dialog.yaml"></i18n>
<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml" src="@/locales/sushi.yaml"></i18n>
<i18n lang="yaml">
en:
  title: Yearly overview
  status:
    no_data: Downloaded, but no data present
    failed: An error occured
    untried: Hasn't been performed yet
    success: Successfully downloaded
  planned: It is already planned to be harvested
  broken: Broken report type
  selected_count: Number of records to harvest
  selected_count_delete: Number of records to delete
  select_help: You can select unsuccessful records in the table
  select_help_delete: You can select records to delete in the table
  harvest_button: Harvest
  delete_button: Delete
  data_harvest: Harvesting credentials
  snack_bar:
    credentials_broken: Entire credentials are broken - can't select item for harvesting.
    report_type_broken: Broken report type - can't select item for harvesting.
  delete_mode: Delete mode
  really_delete: " | Really delete all data for {count} record? This action cannot be reverted without re-harvesting the data. | Really delete all data for {count} records? This action cannot be reverted without re-harvesting the data."
  delete_mode_info: activate to delete existing data
  delete_in_progress: Delete in progress, please wait...

cs:
  title: Yearly overview
  status:
    no_data: Staženo, ale data nenalezena
    failed: Objevila se chyba
    untried: Stahování zatím neproběhlo
    success: Úspěšně staženo
  planned: Stahování bylo naplánováno
  broken: Rozbitý report
  selected_count: Počet záznamů ke stáhnutí
  select_help: Můžete vybrat neúspěšné záznamy z tabulky
  harvest_button: Stáhnout
  data_harvest: Stahuji data k přístupovým udajům
  snack_bar:
    credentials_broken: Přístupové údaje jsou rozbité - položku nelze přidat ke stahování.
    report_type_broken: Rozbitý report - položku nelze přidat ke stahování.
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
            />
          </v-col>
          <v-col cols="auto" class="align-self-start text-right">
            <v-switch
              :label="$t('delete_mode')"
              v-model="deleteMode"
              color="error"
              dense
              :hint="$t('delete_mode_info')"
              persistent-hint
              :disabled="deleteInProgress"
            />
          </v-col>
        </v-row>
        <v-row>
          <v-col>
            <v-data-table
              :items="processedData"
              :headers="headers"
              :footer-props="{ itemsPerPageOptions: itemsPerPageOptions }"
              :loading="loadingDownloads"
              dense
              :options.sync="tableOptions"
              :items-per-page="itemsPerPage"
              :calculate-widths="true"
            >
              <template v-slot:item="row">
                <tr>
                  <td
                    v-if="row.index % reportTypes.length === 0"
                    :rowspan="reportTypes.length"
                  >
                    {{ row.item.year }}
                  </td>
                  <td class="text-center">
                    <v-chip
                      class="mr-1 px-2"
                      :color="row.item['01'].broken ? '#888888' : 'teal'"
                      outlined
                      label
                    >
                      <SushiReportIndicator
                        :report="row.item.report_type"
                        :broken-fn="() => row.item['01'].broken"
                      />
                    </v-chip>
                  </td>
                  <td v-for="month in months" class="pa-0" :key="month">
                    <v-tooltip bottom>
                      <template v-slot:activator="{ on, attrs }">
                        <div v-bind="attrs" v-on="on" class="text-center">
                          <v-btn-toggle
                            v-if="dataReady(row.item, month)"
                            multiple
                            v-model="
                              buttonsSelected[row.item.year + '-' + month]
                            "
                            @change="
                              filterBroken(
                                buttonsSelected,
                                credentials,
                                reportTypes
                              )
                            "
                            dense
                            class="pa-0 d-block"
                          >
                            <v-btn
                              :value="row.item.report_type.id"
                              :key="`${row.item.year}-${month}-${row.item.report_type.code}`"
                              :color="buttonColor(row.item[month])"
                            >
                              <v-icon
                                small
                                :color="
                                  statusIcon(row.item[month].status).color
                                "
                                >{{
                                  statusIcon(row.item[month].status).icon
                                }}</v-icon
                              >
                              <span :class="textClases(row.item[month])"></span>
                            </v-btn>
                          </v-btn-toggle>
                          <span v-else class="text-center d-inline-block">
                            <v-icon
                              small
                              :color="statusIcon(row.item[month].status).color"
                              >{{
                                statusIcon(row.item[month].status).icon
                              }}</v-icon
                            >
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
                        <v-icon small color="error">fa fa-exclamation</v-icon>
                        {{ $t("broken") }}</span
                      >
                      <span v-if="row.item[month].planned"
                        ><br />{{ $t("planned") }}</span
                      >
                    </v-tooltip>
                  </td>
                </tr>
              </template>
            </v-data-table>
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
                      />
                    </v-col>
                  </v-row>
                  <div>
                    <SushiFetchIntentionsListWidget
                      :harvest-id="currentHarvest.pk"
                      ref="intentionsList"
                    />
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
                    >{{ $t("close") }}</v-btn
                  >
                </v-card-actions>
              </v-card>
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
          </v-col>
        </v-row>
      </v-container>
    </v-card-text>
    <v-card-actions>
      <v-container fluid>
        <v-row no-gutters>
          <v-col cols="auto">
            <v-btn
              v-if="deleteMode"
              color="error"
              :disabled="selectedItems.length == 0 || deleteInProgress"
              @click="deleteSelected"
            >
              <v-progress-circular
                small
                indeterminate
                v-if="deleteInProgress"
                color="error"
                class="mr-2"
              />
              <v-icon v-else small class="pr-2">fa fa-trash</v-icon>
              {{ $t("delete_button") }}
            </v-btn>
            <v-btn
              v-else
              @click="triggerHarvest"
              :disabled="selectedItems.length == 0 || deleteInProgress"
              color="primary"
            >
              <v-icon small class="pr-2">fa fa-download</v-icon>
              {{ $t("harvest_button") }}
            </v-btn>
          </v-col>
          <v-col v-if="deleteInProgress" class="align-self-center">
            <div class="pl-4 warning--text">
              {{ $t("delete_in_progress") }}
            </div>
          </v-col>
        </v-row>
      </v-container>
      <v-spacer></v-spacer>
      <v-btn @click="closeDialog()" class="mr-4" :right="true">{{
        $t("close")
      }}</v-btn>
    </v-card-actions>
  </v-card>
</template>

<script>
import axios from "axios";
import { mapActions } from "vuex";
import { ymFirstDay, ymLastDay } from "@/libs/dates";
import SushiFetchIntentionsListWidget from "@/components/sushi/SushiFetchIntentionsListWidget";
import SushiCredentialsOverviewHeaderWidget from "@/components/sushi/SushiCredentialsOverviewHeaderWidget";
import SushiReportIndicator from "@/components/sushi/SushiReportIndicator";
import { dataStateToIcon } from "@/libs/data-state";

export default {
  name: "SushiCredentialsDataDialog",
  components: {
    SushiFetchIntentionsListWidget,
    SushiCredentialsOverviewHeaderWidget,
    SushiReportIndicator,
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
      tableOptions: {
        sortBy: ["year"],
        sortDesc: [true],
      },
      currentHarvest: null,
      showHarvestDialog: false,
      deleteMode: true,
      deleteInProgress: false,
    };
  },
  computed: {
    itemsPerPageOptions() {
      return [
        this.reportTypes.length,
        this.reportTypes.length * 2,
        this.reportTypes.length * 3,
      ];
    },
    itemsPerPage() {
      return this.reportTypes.length;
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
        for (const report_type of this.reportTypes) {
          let record = {
            year: year_data.year,
            report_type: report_type,
          };
          for (const month of this.months) {
            for (const row of year_data[month]) {
              if (row.counter_report.code == report_type.code) {
                record[month] = {
                  status: row.status,
                  planned: row.planned,
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
    reportTypes() {
      let result = [];
      if (this.fetchedData.length > 0) {
        for (const rt of this.fetchedData[0]["01"]) {
          result.push({
            broken: rt.broken,
            code: rt.counter_report.code,
            id: rt.counter_report.id,
            name: rt.counter_report.name,
          });
        }
      }
      return result;
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
            counter_report: rt,
          });
        }
      }
      return result;
    },
    headers() {
      let res = [
        { text: this.$t("year"), value: "year", class: "wrap" },
        {
          text: this.$t("labels.report_type"),
          value: "counter_report",
          class: "wrap",
          align: "center",
        },
      ];
      for (let i = 1; i <= 12; i++) {
        let padded = `${i}`.padStart(2, "0");
        let shortMonthName = new Date(2020, i - 1, 1).toLocaleString(
          this.$i18n.locale,
          { month: "short" }
        );
        res.push({
          text: shortMonthName,
          value: `${padded}`,
          sortable: false,
          align: "center",
          width: 50,
        });
      }
      return res;
    },
    totalCount() {
      return this.processedData.length;
    },
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
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
    isStatusSelectable(status) {
      if (this.deleteMode || (status !== "no_data" && status !== "success"))
        return true;
      return false;
    },
    dataReady(item, month) {
      let year = parseInt(item.year);
      let month_int = parseInt(month);
      if (!this.isStatusSelectable(item[month].status))
        // do not allow re-harvesting of successful downloads
        return false;
      let current = new Date();
      let current_year = current.getFullYear();
      let current_month = current.getMonth() + 1;
      return year < current_year ||
        (year == current_year && month_int < current_month)
        ? true
        : false;
    },
    buttonColor: (report) => {
      if (report.planned) {
        return "primary lighten-5";
      }
      return "";
    },
    textClases: (report) => {
      if (report.planned) {
        return ["font-weight-black", "primary--text"];
      }
      return [];
    },
    statusIcon: (state) => {
      let res = dataStateToIcon(state);
      return res;
    },
    filterBroken(selected, credentials, reportTypes) {
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
      let brokenIds = reportTypes.filter((rt) => rt.broken).map((e) => e.id);
      let broken_report_type = false;
      Object.keys(selected).forEach((key) => {
        let orig_len = selected[key].length;
        selected[key] = selected[key].filter(
          (rt_id) => !brokenIds.includes(rt_id)
        );
        broken_report_type =
          broken_report_type || orig_len != selected[key].length;
      });
      if (broken_report_type) {
        this.showSnackbar({
          content: this.$t("snack_bar.report_type_broken"),
          color: "error",
        });
      }
    },
    async deleteSelected() {
      const res = await this.$confirm(
        this.$tc("really_delete", this.selectedItems.length),
        {
          title: this.$t("confirm_delete"),
          buttonTrueText: this.$t("delete"),
          buttonFalseText: this.$t("cancel"),
        }
      );
      if (res) {
        this.deleteInProgress = true;
        try {
          await axios.post(
            "/api/scheduler/fetch-intention-delete/",
            this.selectedItems
          );
          await this.loadCredentialsData();
          this.validateSelection();
        } catch (error) {
          this.showSnackbar({
            content: "Error deleting data: " + error,
            color: "error",
          });
        } finally {
          this.deleteInProgress = false;
        }
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
          if (this.isStatusSelectable(match.status)) {
            newSelection[yearMonth] = trs;
          }
        }
      }
      this.buttonsSelected = newSelection;
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
