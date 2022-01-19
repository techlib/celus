<i18n lang="yaml" src="../locales/common.yaml"></i18n>
<i18n lang="yaml">
en:
  table_header:
    created: Created
    last_processed: Last download
    manual: Manually created
    finished: Finished
    attempts: Attempts
    last_attempt: Finish planned
    month: Month
  downloads: Downloads
  tooltip:
    automatic: Automatically planned harvesting.
    manual: Manually planned harvesting.
    date_not_set: Date is not set.
    harvest_details: Show harvest details
    broken_credentials: "|There is {n} record which can't be downloaded due to broken credentials.|There are {n} records which can't be downloaded due to broken credentials."
  filter:
    finished:
      title: Finished
      ready: Yes
      working: No
      all: All
    manual:
      title: Manually created
      all: All
      automatic: No
      manual: Yes
    broken:
      title: Broken
      all: All
      no: No
      yes: Yes
    month: Harvested month

cs:
  table_header:
    created: Vytvořeno
    last_processed: Poslední stahování
    manual: Manuálně vytvořeno
    finished: Hotovo
    last_attempt: Dokončení plánováno
    attempts: Pokusy
    month: Měsíc
  downloads: Stahování
  tooltip:
    automatic: Automaticky naplánované stahování.
    manual: Manuálně naplánované stahování.
    date_not_set: Datum není určeno.
    harvest_details: Zobraz detail stahování
    broken_credentials: "|Obsahuje {n} záznam, který nemůže být stažen, kvůli rozbitým přístupovým údajům.|Obsahuje {n} záznamy, které nemohou být stažen, kvůli rozbitým přístupovým údajům.|Obsahuje {n} záznamů, které nemohou být stažen, kvůli rozbitým přístupovým údajům."
  filter:
    finished:
      title: Dokončeno
      ready: Ano
      working: Ne
      all: Všechno
    manual:
      title: Manuálně vytvořeno
      all: Všechno
      automatic: Ne
      manual: Ano
    broken:
      title: Rozbité
      all: Všechno
      no: Ne
      yes: Ano
    month: Stahovaný měsíc
</i18n>

<template>
  <v-container fluid>
    <v-row class="px-3">
      <v-col cols="auto">
        <v-select
          :items="filterFinishedList"
          v-model="filterFinished"
          :label="$t('filter.finished.title')"
        ></v-select>
      </v-col>
      <v-col cols="auto">
        <v-select
          :items="filterManualList"
          v-model="filterManual"
          :label="$t('filter.manual.title')"
        ></v-select>
      </v-col>
      <v-col cols="auto">
        <v-select
          :items="filterBrokenList"
          v-model="filterBroken"
          :label="$t('filter.broken.title')"
        ></v-select>
      </v-col>
      <v-col cols="auto">
        <MonthEntry
          v-model="filterMonth"
          :label="$t('filter.month')"
        ></MonthEntry>
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <v-data-table
          :items="tableData"
          :headers="headers"
          :footer-props="{ itemsPerPageOptions: [10, 25, 50, 100] }"
          :loading="loading"
          dense
          :options.sync="tableOptions"
          :server-items-length="totalCount"
        >
          <template v-slot:item.pk="{ item }">
            <v-tooltip bottom>
              <template v-slot:activator="{ on }">
                <v-btn
                  text
                  small
                  color="secondary"
                  @click.stop="
                    selectHarvest(item.pk);
                    showHarvestDialog = true;
                  "
                  v-on="on"
                >
                  <v-icon left small>fa-external-link-alt</v-icon>
                  <span v-if="item.broken">
                    <v-badge :content="item.broken" color="error">
                      {{ item.pk }}
                    </v-badge>
                  </span>
                  <span v-else>
                    {{ item.pk }}
                  </span>
                </v-btn>
              </template>
              <span
                ><strong>{{ $t("tooltip.harvest_details") }}</strong></span
              >
              <br />
              <span v-if="item.broken">{{
                $tc("tooltip.broken_credentials", item.broken)
              }}</span>
            </v-tooltip>
          </template>
          <template v-slot:item.manual="{ item }">
            <CheckMark
              :value="item.manual"
              :true-tooltip="$t('tooltip.manual')"
              :false-tooltip="$t('tooltip.automatic')"
            />
          </template>
          <template v-slot:item.created="{ item }">
            <span v-html="formatDateTime(item.created)"></span>
          </template>
          <template v-slot:item.last_processed="{ item }">
            <span
              v-html="
                item.last_processed ? formatDateTime(item.last_processed) : '-'
              "
            ></span>
          </template>
          <template v-slot:item.month="{ item }">
            <span v-html="formatYM(item.start_date)"></span>
            <div v-if="formatYM(item.start_date) != formatYM(item.end_date)">
              <span v-html="' ' + formatYM(item.end_date)"></span>
            </div>
          </template>
          <template #item.lastAttempt="{ item }">
            <span v-if="item.finished || !item.lastAttempt">-</span>
            <span v-else v-html="formatDateTime(item.lastAttempt)"></span>
          </template>
        </v-data-table>

        <v-dialog
          v-model="showHarvestDialog"
          v-if="currentHarvest"
          content-class="top-dialog"
          max-width="1320px"
        >
          <v-card>
            <v-card-text class="pb-0">
              <v-row>
                <v-col>
                  <h3 class="pt-3 text-h5">{{ $t("downloads") }}</h3>
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
                >{{ $t("actions.close") }}</v-btn
              >
            </v-card-actions>
          </v-card>
        </v-dialog>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import cancellation from "@/mixins/cancellation";
import { mapActions, mapGetters } from "vuex";
import {
  isoDateTimeFormat,
  isoDateTimeFormatSpans,
  parseDateTime,
  ymDateFormat,
} from "@/libs/dates";
import CheckMark from "@/components/util/CheckMark";
import MonthEntry from "@/components/util/MonthEntry";
import formatRelative from "date-fns/formatRelative";
import SushiFetchIntentionsListWidget from "@/components/sushi/SushiFetchIntentionsListWidget";

export default {
  name: "HarvestsTable",
  mixins: [cancellation],

  components: {
    SushiFetchIntentionsListWidget,
    CheckMark,
    MonthEntry,
  },

  props: {
    retryInterval: { default: 1000, type: Number },
    showOrganization: { default: false, type: Boolean },
    showPlatform: { default: false, type: Boolean },
    refreshInterval: { default: 10000, type: Number },
  },

  data() {
    return {
      harvestsData: [], // raw request data
      tableData: [], // processed data
      showHarvestDialog: false,
      currentHarvest: null,
      orderBy: ["harvest.pk"],
      loading: false,
      filterFinished: "",
      filterManual: "",
      filterMonth: "",
      filterBroken: "",
      now: new Date(),
      totalCount: 0,
      tableOptions: {
        sortBy: ["pk"],
        sortDesc: [true],
      },
      lastFetchedTime: null,
      lastFetchTimer: null,
    };
  },

  computed: {
    ...mapGetters({
      dateFnOptions: "dateFnOptions",
    }),
    harvestsUrl() {
      let filterFinished = "";
      switch (this.filterFinished) {
        case "working":
          filterFinished = "&finished=0";
          break;
        case "ready":
          filterFinished = "&finished=1";
          break;
      }
      let filterManual = "";
      switch (this.filterManual) {
        case "automatic":
          filterManual = "&automatic=1";
          break;
        case "manual":
          filterManual = "&automatic=0";
          break;
      }
      let filterBroken = "";
      switch (this.filterBroken) {
        case "yes":
          filterBroken = "&broken=1";
          break;
        case "no":
          filterBroken = "&broken=0";
          break;
      }
      let filterMonth = this.filterMonth ? `&month=${this.filterMonth}` : "";
      let sortBy = this.tableOptions.sortBy ? this.tableOptions.sortBy[0] : "";
      let sortDesc = this.tableOptions.sortDesc
        ? this.tableOptions.sortDesc[0]
        : false;
      switch (sortBy) {
        case "finishedRatio":
          sortBy = "finished";
          break;
        case "manual":
          sortBy = "automatic";
          sortDesc = !sortDesc;
          break;
        case "lastAttempt":
          sortBy = "last_attempt_date";
          break;
        case "attempts":
          sortBy = "attempt_count";
          break;
        case "month":
          sortBy = "start_date";
          break;
      }
      return `/api/scheduler/harvest/?page=${this.tableOptions.page}&page_size=${this.tableOptions.itemsPerPage}&order_by=${sortBy}&desc=${sortDesc}${filterFinished}${filterManual}${filterMonth}${filterBroken}`;
    },
    headers() {
      const headersHead = [
        {
          text: "#",
          value: "pk",
          class: "wrap",
        },
      ];
      const headersTail = [
        {
          text: this.$t("title_fields.platforms"),
          value: "platforms",
          sortable: false,
        },
        {
          text: this.$t("table_header.created"),
          value: "created",
          class: "wrap",
        },
        {
          text: this.$t("table_header.last_processed"),
          value: "last_processed",
          class: "wrap",
        },
        {
          text: this.$t("table_header.manual"),
          value: "manual",
          class: "wrap",
        },
        {
          text: this.$t("table_header.month"),
          value: "month",
          class: "wrap",
        },
        {
          text: this.$t("table_header.finished"),
          value: "finishedRatio",
          align: "end",
        },
        {
          text: this.$t("table_header.attempts"),
          value: "attempts",
          align: "end",
        },
        { text: this.$t("table_header.last_attempt"), value: "lastAttempt" },
      ];
      let headersMiddle = [];
      if (this.showOrganization) {
        headersMiddle.push({
          text: this.$t("title_fields.organizations"),
          value: "organizations",
          sortable: false,
        });
      }
      return [...headersHead, ...headersMiddle, ...headersTail];
    },
    filterFinishedList() {
      return [
        {
          value: "",
          text: this.$t("filter.finished.all"),
        },
        {
          value: "ready",
          text: this.$t("filter.finished.ready"),
        },
        {
          value: "working",
          text: this.$t("filter.finished.working"),
        },
      ];
    },
    filterBrokenList() {
      return [
        {
          value: "",
          text: this.$t("filter.broken.all"),
        },
        {
          value: "yes",
          text: this.$t("filter.broken.yes"),
        },
        {
          value: "no",
          text: this.$t("filter.broken.no"),
        },
      ];
    },
    filterManualList() {
      return [
        {
          value: "",
          text: this.$t("filter.manual.all"),
        },
        {
          value: "automatic",
          text: this.$t("filter.manual.automatic"),
        },
        {
          value: "manual",
          text: this.$t("filter.manual.manual"),
        },
      ];
    },
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    async fetchHarvestsData() {
      this.loading = true;
      let result = await this.http({
        url: this.harvestsUrl,
        group: "harvest-list",
      });
      this.loading = false;
      if (!result.error) {
        this.totalCount = result.response.data.count;
        this.harvestsData = result.response.data.results;
        this.dataToTable(result.response.data.results);
        this.lastFetchedTime = new Date();
      }
    },
    async selectHarvest(id) {
      const candidates = this.harvestsData.filter((item) => item.pk === id);
      if (candidates.length > 0) {
        this.currentHarvest = candidates[0];
      }
    },
    dataToTable(harvests) {
      let res = [];
      for (let rec of harvests) {
        res.push({
          pk: rec.pk,
          created: parseDateTime(rec.created),
          broken: rec.broken,
          last_processed: parseDateTime(rec.last_processed),
          manual: rec.automatic === null,
          finished: 0 === rec.stats.planned,
          finishedRatio: `${rec.stats.total - rec.stats.planned}/${
            rec.stats.total
          }`,
          attempts: rec.stats.attempt_count,
          organizations: rec.organizations
            .map((item) => item.short_name || item.name)
            .join(", "),
          platforms: rec.platforms
            .map((item) => item.short_name || item.name)
            .join(", "),
          lastAttempt: parseDateTime(rec.last_attempt_date),
          start_date: rec.start_date,
          end_date: rec.end_date,
        });
      }
      this.tableData = res;
    },
    formatDateTime(value) {
      return isoDateTimeFormatSpans(value);
    },
    formatDateTimePlain(value) {
      if (value) {
        return isoDateTimeFormat(value);
      }
      return this.$t("tooltip.date_not_set");
    },
    formatDateTimeRelative(value) {
      if (value) {
        return formatRelative(value, this.now, this.dateFnOptions);
      }
      return "-";
    },
    formatYM(value) {
      if (value) {
        return ymDateFormat(parseDateTime(value));
      }
      return "-";
    },
  },

  created() {
    this.now = new Date();
  },

  mounted() {
    this.fetchHarvestsData();
    setInterval(() => {
      this.now = new Date();
    }, 10000); // we do not need it that often
  },

  watch: {
    harvestsUrl() {
      this.fetchHarvestsData();
    },
    lastFetchedTime() {
      if (this.lastFetchTimer) {
        clearTimeout(this.lastFetchTimer);
      }
      this.lastFetchTimer = setTimeout(() => {
        this.fetchHarvestsData();
      }, this.refreshInterval);
    },
    showHarvestDialog() {
      if (!this.showHarvestDialog) {
        this.$refs.intentionsList.stop();
        this.fetchHarvestsData();
      }
    },
  },
};
</script>
