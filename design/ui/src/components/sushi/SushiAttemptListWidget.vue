<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<i18n lang="yaml" src="@/locales/dialog.yaml"></i18n>

<i18n lang="yaml">
en:
  sushi_fetch_attempts: SUSHI fetch attempts
  timestamp: Time of attempt
  show_raw_data: Show raw data
  show_chart: Show charts
  data_file: Data file
  used_url: Used URL

cs:
  sushi_fetch_attempts: Pokusy o stažení SUSHI
  timestamp: Čas pokusu
  show_raw_data: Zobrazit data
  show_chart: Zobrazit grafy
  data_file: Datový soubor
  used_url: Použitá URL
</i18n>

<template>
  <v-card>
    <v-card-title>{{ $t("sushi_fetch_attempts") }}</v-card-title>
    <v-card-text class="pb-0">
      <v-container fluid>
        <v-row v-if="!intentionId">
          <v-col cols="12" md="6">
            <SushiCredentialsOverviewHeaderWidget
              v-if="credentials"
              :credentials-name="credentials.title"
              :organization="credentials.organization"
              :platform="credentials.platform"
              :counter-version="credentials.counter_version"
            ></SushiCredentialsOverviewHeaderWidget>
          </v-col>
          <v-spacer></v-spacer>
          <v-col cols="12" md="6" lg="4" xl="3">
            <FetchAttemptModeFilter
              v-model="historyMode"
              @update:modelValue="page = 1"
            />
          </v-col>
        </v-row>
        <v-row>
          <v-col>
            <v-data-table-server
              :items="intentions"
              :headers="headers"
              v-model:expanded="expandedRows"
              item-key="pk"
              item-value="pk"
              v-model:sort-by="orderBy"
              v-model:items-per-page="pageSize"
              :loading="loading"
              :items-per-page-options="[5, 10, 25]"
              :items-length="intentionCount"
              v-model:page="page"
              density="default"
            >
              <template #headers="{ columns }">
                <TableCustomSort
                  :columns="columns"
                  v-model:externalOrderBy="orderBy"
                />
              </template>
              <template #item.data-table-expand="{ item }">
                <v-btn
                  icon
                  variant="text"
                  size="small"
                  @click="toggleExpand(item)"
                >
                  <v-icon>
                    {{
                      expandedRows.includes(item.pk)
                        ? "fas fa-caret-down"
                        : "fas fa-caret-right"
                    }}
                  </v-icon>
                </v-btn>
              </template>

              <template #item.status="{ item }">
                <SushiFetchIntentionStateIcon
                  :intention="item"
                ></SushiFetchIntentionStateIcon>
              </template>
              <template #item.timestamp="{ item }">
                <span
                  v-html="
                    item.attempt && formatDateTime(item.attempt.timestamp)
                  "
                ></span>
              </template>
              <template #item.start_date="{ item }">
                {{ ymDateFormat(item.start_date) }}
              </template>
              <template #expanded-row="{ item, columns }">
                <tr class="item_expanded_space">
                  <td :colspan="columns.length">
                    <div class="d-flex justify-space-between py-4">
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
                        <AttemptExtractedData
                          :attempt="item.attempt"
                          :counter-report-version="item.counter_report_version"
                        />
                      </div>
                      <div class="ml-auto" v-if="!!item.attempt.used_url">
                        <a :href="item.attempt.used_url" target="_blank">
                          {{ $t("used_url") }}
                        </a>
                      </div>
                      <div class="ml-auto">
                        <a
                          v-if="item.attempt && item.attempt.data_file"
                          :href="item.attempt.data_file"
                          target="_blank"
                        >
                          {{ $t("data_file") }}</a
                        ><span class="caption">
                          ({{ filesize(item.attempt.file_size) }})</span
                        >
                      </div>
                    </div>
                  </td>
                </tr>
              </template>
              <template #item.actions="{ item }">
                <v-tooltip
                  location="bottom"
                  v-if="item.attempt && item.attempt.import_batch"
                >
                  <template v-slot:activator="{ props }">
                    <v-btn
                      icon
                      size="small"
                      color="secondary"
                      @click.stop="
                        selectedBatch = item.attempt.import_batch;
                        dialogType = 'data';
                        showBatchDialog = true;
                      "
                      v-bind="props"
                      variant="text"
                    >
                      <v-icon size="small">fa fa-microscope</v-icon>
                    </v-btn>
                  </template>
                  <span>{{ $t("show_raw_data") }}</span>
                </v-tooltip>
                <v-tooltip
                  location="bottom"
                  v-if="item.attempt && item.attempt.import_batch"
                >
                  <template v-slot:activator="{ props }">
                    <v-btn
                      icon
                      variant="text"
                      size="small"
                      color="secondary"
                      @click.stop="
                        selectedBatch = item.attempt.import_batch;
                        dialogType = 'chart';
                        showBatchDialog = true;
                      "
                      v-bind="props"
                    >
                      <v-icon size="small">fas fa-chart-bar</v-icon>
                    </v-btn>
                  </template>
                  <span>{{ $t("show_chart") }}</span>
                </v-tooltip>
              </template>
            </v-data-table-server>
          </v-col>
        </v-row>
      </v-container>
    </v-card-text>
    <v-card-actions>
      <v-spacer></v-spacer>
      <v-btn
        @click="$emit('close')"
        variant="elevated"
        color="defaultButton"
        class="mb-3 mr-4"
        >{{ $t("close") }}</v-btn
      >
    </v-card-actions>
    <v-dialog v-model="showBatchDialog" v-if="showBatchDialog">
      <v-card>
        <v-card-text class="pb-0">
          <div class="pt-5">
            <AccessLogList
              v-if="dialogType === 'data'"
              :import-batch="selectedBatch"
            ></AccessLogList>
            <ImportBatchChart
              v-else-if="dialogType === 'chart'"
              :import-batch-id="selectedBatch"
            ></ImportBatchChart>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn
            @click="showBatchDialog = false"
            class="mb-3 mr-4"
            variant="elevated"
            color="defaultButton"
            >{{ $t("actions.close") }}</v-btn
          >
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
import { filesize } from "filesize";
import TableCustomSort from "../tables/TableCustomSort.vue";
import { ymDateFormat } from "@/libs/dates";

export default {
  name: "SushiAttemptListWidget",
  components: {
    AttemptExtractedData,
    SushiFetchIntentionStateIcon,
    AccessLogList,
    ImportBatchChart,
    FetchAttemptModeFilter,
    SushiCredentialsOverviewHeaderWidget,
    TableCustomSort,
  },
  props: {
    credentials: { required: false },
    intentionId: { required: false },
  },
  data() {
    return {
      intentions: [],
      expandedRows: [],
      intentionCount: 0,
      orderBy: [{ key: "start_date", order: "desc" }],
      pageSize: 5,
      page: 1,
      showBatchDialog: false,
      selectedBatch: null,
      dialogType: "",
      loading: false,
      historyMode: "success_and_current",
      orderingRemap: new Map([
        ["counter_report_verbose.code", "counter_report__code"],
      ]),
    };
  },
  computed: {
    listUrl() {
      if (this.intentionId) {
        return `/api/scheduler/intention/${this.intentionId}`;
      }
      if (!this.credentials) {
        return "";
      }
      let base = `/api/scheduler/intention/?format=json&attempt=1&mode=${this.historyMode}&credentials=${this.credentials.pk}`;
      // sorting
      base += `&page_size=${this.pageSize}&page=${this.page}`;
      if (this.orderBy.length) {
        // some order_by's have to be remapped for the backend to understand it
        let order_by_param =
          typeof this.orderBy === "object" ? this.orderBy[0].key : this.orderBy;
        if (this.orderingRemap.has(order_by_param))
          order_by_param = this.orderingRemap.get(order_by_param);
        base += `&order_by=${order_by_param}`;
        base += `&desc=${this.orderBy[0].order == "desc"}`;
      }
      return base;
    },
    headers() {
      let ret = [
        {
          title: "",
          value: "data-table-expand",
          align: "start",
          sortable: false,
        },
        {
          title: this.$t("title_fields.status"),
          value: "status",
          sortable: false,
        },
        {
          title: this.$t("timestamp"),
          value: "timestamp",
          key: "timestamp",
          order: "reverse",
        },
        {
          title: this.$t("month"),
          value: "start_date",
          key: "start_date",
          order: "reverse",
        },
        {
          title: this.$t("title_fields.error_code"),
          value: "error_code",
          key: "error_code",
        },
        {
          title: this.$t("report"),
          value: "counter_report_verbose.code",
          key: "counter_report_verbose.code",
        },
        {
          title: this.$t("title_fields.actions"),
          value: "actions",
          key: "actions",
          sortable: false,
          width: "115px",
          align: "center",
        },
      ];
      return ret;
    },
  },
  methods: {
    filesize,
    ymDateFormat,
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    toggleExpand(item) {
      const index = this.expandedRows.indexOf(item.pk);
      if (index > -1) {
        this.expandedRows.splice(index, 1);
      } else {
        this.expandedRows.push(item.pk);
      }
    },
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
