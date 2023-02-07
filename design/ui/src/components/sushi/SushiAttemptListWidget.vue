<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml" src="@/locales/dialog.yaml"></i18n>
<i18n lang="yaml">
en:
  sushi_fetch_attempts: Sushi fetch attempts
  timestamp: Time of attempt
  show_success: Show successful
  show_failure: Show failures
  show_raw_data: Show raw data
  show_chart: Show charts
  not_older_than: Not older than
  counter_version: Counter version
  data_file: Data file

cs:
  sushi_fetch_attempts: Pokusy o stažení Sushi
  timestamp: Čas pokusu
  show_success: Zobrazit úspěšné
  show_failure: Zobrazit neúspěšné
  show_raw_data: Zobrazit data
  show_chart: Zobrazit grafy
  not_older_than: Ne starší než
  counter_version: Verze Counter
  data_file: Datový soubor
</i18n>

<template>
  <v-card>
    <v-card-title>{{ $t("sushi_fetch_attempts") }}</v-card-title>
    <v-card-text class="pb-0">
      <v-container fluid>
        <v-row v-if="!intentionId">
          <v-col cols="12" md="6">
            <SushiCredentialsOverviewHeaderWidget
              :organization="organization"
              :platform="platform"
              :report="report"
              :counter-version="counterVersion"
              :month="month"
              :from-date="fromDate"
            />
          </v-col>
          <v-spacer></v-spacer>
          <v-col cols="12" md="6">
            <v-container fluid class="pa-0">
              <v-row justify="end">
                <v-col cols="auto" class="py-0">
                  <FetchAttemptModeFilter v-model="historyMode" />
                </v-col>
                <!--v-col cols="auto" class="py-0">
                                    <v-switch v-model="showSuccess" :label="$t('show_success')" color="success" dense></v-switch>
                                </v-col>
                                <v-col cols="auto" class="py-0">
                                    <v-switch v-model="showFailure" :label="$t('show_failure')" color="error" dense></v-switch>
                                </v-col-->
              </v-row>
            </v-container>
          </v-col>
        </v-row>
        <v-row>
          <v-col>
            <v-data-table
              :items="filteredIntentions"
              :headers="headers"
              show-expand
              :expanded.sync="expandedRows"
              item-key="pk"
              :sort-by.sync="orderBy"
              :sort-desc.sync="orderDesc"
              :items-per-page.sync="pageSize"
              :loading="loading"
              :footer-props="{ itemsPerPageOptions: [5, 10, 25] }"
              :server-items-length="intentionCount"
              :page.sync="page"
            >
              <template #item.status="{ item }">
                <SushiFetchIntentionStateIcon :intention="item" />
              </template>
              <template #item.timestamp="{ item }">
                <span
                  v-html="
                    item.attempt && formatDateTime(item.attempt.timestamp)
                  "
                ></span>
              </template>
              <template #expanded-item="{ item, headers }">
                <td :colspan="headers.length">
                  <div class="d-flex justify-space-between">
                    <div>
                      <div class="d-flex" v-if="item.attempt.log">
                        <div class="font-weight-bold pr-2">
                          {{ $t("title_fields.log") }}
                        </div>
                        <div class="pre">
                          {{ item.attempt.log }}
                        </div>
                      </div>
                      <!-- extracted data -->
                      <AttemptExtractedData :attempt="item.attempt" />
                    </div>
                    <div class="ml-auto">
                      <a
                        v-if="item.attempt && item.attempt.data_file"
                        :href="item.attempt.data_file"
                        target="_blank"
                      >
                        {{ $t("data_file") }}
                      </a>
                    </div>
                  </div>
                </td>
              </template>
              <template #item.data-table-expand="{ isExpanded, expand }">
                <v-icon @click="expand(!isExpanded)" small>{{
                  isExpanded ? "fa-angle-down" : "fa-angle-right"
                }}</v-icon>
              </template>
              <template #item.actions="{ item }">
                <v-tooltip
                  bottom
                  v-if="item.attempt && item.attempt.import_batch"
                >
                  <template v-slot:activator="{ on }">
                    <v-btn
                      icon
                      small
                      color="secondary"
                      @click.stop="
                        selectedBatch = item.attempt.import_batch;
                        dialogType = 'data';
                        showBatchDialog = true;
                      "
                      v-on="on"
                    >
                      <v-icon small>fa-microscope</v-icon>
                    </v-btn>
                  </template>
                  <span>{{ $t("show_raw_data") }}</span>
                </v-tooltip>
                <v-tooltip
                  bottom
                  v-if="item.attempt && item.attempt.import_batch"
                >
                  <template v-slot:activator="{ on }">
                    <v-btn
                      icon
                      small
                      color="secondary"
                      @click.stop="
                        selectedBatch = item.attempt.import_batch;
                        dialogType = 'chart';
                        showBatchDialog = true;
                      "
                      v-on="on"
                    >
                      <v-icon small>fa-chart-bar</v-icon>
                    </v-btn>
                  </template>
                  <span>{{ $t("show_chart") }}</span>
                </v-tooltip>
              </template>
            </v-data-table>
          </v-col>
        </v-row>
      </v-container>
    </v-card-text>
    <v-card-actions>
      <v-spacer></v-spacer>
      <v-btn @click="$emit('close')" class="mb-3 mr-4">{{ $t("close") }}</v-btn>
    </v-card-actions>

    <v-dialog v-model="showBatchDialog" v-if="showBatchDialog">
      <v-card>
        <v-card-text class="pb-0">
          <div class="pt-5">
            <AccessLogList
              v-if="dialogType === 'data'"
              :import-batch="selectedBatch"
            />
            <ImportBatchChart
              v-else-if="dialogType === 'chart'"
              :import-batch-id="selectedBatch"
            />
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="showBatchDialog = false" class="mb-3 mr-4">{{
            $t("actions.close")
          }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card>
</template>

<script>
import { mapActions } from "vuex";
import axios from "axios";
import AccessLogList from "../AccessLogList";
import ImportBatchChart from "../ImportBatchChart";
import FetchAttemptModeFilter from "./FetchAttemptModeFilter";
import SushiFetchIntentionStateIcon from "@/components/sushi/SushiFetchIntentionStateIcon";
import SushiCredentialsOverviewHeaderWidget from "@/components/sushi/SushiCredentialsOverviewHeaderWidget";
import { isoDateTimeFormatSpans } from "@/libs/dates";
import AttemptExtractedData from "@/components/sushi/AttemptExtractedData";

export default {
  name: "SushiAttemptListWidget",
  components: {
    AttemptExtractedData,
    SushiFetchIntentionStateIcon,
    AccessLogList,
    ImportBatchChart,
    FetchAttemptModeFilter,
    SushiCredentialsOverviewHeaderWidget,
  },
  props: {
    credentials: { required: false },
    organization: { required: false },
    platform: { required: false },
    report: { required: false },
    fromDate: { required: false },
    month: { required: false },
    counterVersion: { required: false },
    intentionId: { required: false },
  },
  data() {
    return {
      intentions: [],
      expandedRows: [],
      intentionCount: 0,
      showSuccess: true,
      showFailure: true,
      orderBy: ["timestamp"],
      orderDesc: [true],
      pageSize: 5,
      page: 1,
      showBatchDialog: false,
      selectedBatch: null,
      dialogType: "",
      loading: false,
      hideObsolete: true,
      historyMode: "success_and_current",
      orderingRemap: new Map([
        ["counter_report_verbose.code", "counter_report__code"],
        ["organization.name", "credentials__organization__name"],
      ]),
    };
  },
  computed: {
    listUrl() {
      if (this.intentionId) {
        return `/api/scheduler/intention/${this.intentionId}`;
      }
      if (
        !(this.organization || this.platform || this.report || this.credentials)
      ) {
        return "";
      }
      let base = `/api/scheduler/intention/?format=json&attempt=1&mode=${this.historyMode}`;
      if (this.credentials) {
        base += `&credentials=${this.credentials.pk}`;
      }
      if (this.organization) {
        base += `&organization=${this.organization.pk}`;
      }
      if (this.platform) {
        base += `&platform=${this.platform.pk}`;
      }
      if (this.report) {
        base += `&report=${this.report.pk}`;
      }
      if (this.fromDate) {
        base += `&date_from=${this.fromDate}`;
      }
      if (this.month) {
        base += `&month=${this.month.pk}`;
      }
      if (this.counterVersion) {
        base += `&counter_version=${this.counterVersion}`;
      }
      // sorting
      base += `&page_size=${this.pageSize}&page=${this.page}`;
      if (this.orderBy.length) {
        // some order_by's have to be remapped for the backend to understand it
        let order_by_param =
          typeof this.orderBy === "object" ? this.orderBy[0] : this.orderBy;
        console.debug(order_by_param, this.orderingRemap.has(order_by_param));
        if (this.orderingRemap.has(order_by_param))
          order_by_param = this.orderingRemap.get(order_by_param);
        base += `&order_by=${order_by_param}`;
        if (this.orderDesc.length) {
          base += `&desc=${this.orderDesc[0]}`;
        }
      }
      return base;
    },
    headers() {
      let ret = [
        {
          text: this.$t("title_fields.status"),
          value: "status",
          sortable: false,
        },
        {
          text: this.$t("timestamp"),
          value: "timestamp",
        },
        {
          text: this.$t("title_fields.start_date"),
          value: "start_date",
        },
        {
          text: this.$t("title_fields.end_date"),
          value: "end_date",
        },
        {
          text: this.$t("title_fields.error_code"),
          value: "error_code",
        },
      ];
      if (!this.organization) {
        ret.push({ text: this.$t("organization"), value: "organization.name" });
      }
      if (!this.report) {
        ret.push({
          text: this.$t("report"),
          value: "counter_report_verbose.code",
        });
      }
      ret.push({
        text: this.$t("title_fields.actions"),
        value: "actions",
        sortable: false,
      });

      return ret;
    },
    filteredIntentions() {
      let out = this.intentions;
      if (!this.showSuccess) {
        out = out.filter((item) => !item.processing_success);
      }
      if (!this.showFailure) {
        out = out.filter((item) => item.processing_success);
      }
      return out;
    },
  },
  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    async loadIntentions() {
      if (!this.listUrl) {
        return;
      }
      this.loading = true;
      try {
        let response = await axios.get(this.listUrl);
        if (this.intentionId) {
          this.intentions = [response.data];
          this.intentionCount = 1;
        } else {
          this.intentions = response.data.results;
          this.intentionCount = response.data.count;
        }
      } catch (error) {
        this.intentions = [];
        this.showSnackbar({
          content: "Error fetching SUSHI attempt data: " + error,
          color: "error",
        });
      } finally {
        this.loading = false;
      }
    },
    formatDateTime(value) {
      return isoDateTimeFormatSpans(value);
    },
    cleanup() {
      this.intentions = [];
    },
  },

  watch: {
    listUrl() {
      this.loadIntentions();
    },
  },
  mounted() {
    this.loadIntentions();
  },
};
</script>

<style lang="scss">
.pre {
  font-family: Courier, monospace;
  color: #666666;
  white-space: pre-wrap;
}
</style>
