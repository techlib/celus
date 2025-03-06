<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

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
    broken_credentials: "There is {n} record which can't be downloaded due to broken credentials. | There are {n} records which can't be downloaded due to broken credentials."
  filter:
    finished:
      title: Finished
      ready: Yes
      unfinished: No
      all: All
      working: Working
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
    platforms: Platforms
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
    broken_credentials: "Obsahuje {n} záznam, který nemůže být stažen, kvůli rozbitým přístupovým údajům. | Obsahuje {n} záznamy, které nemohou být stažen, kvůli rozbitým přístupovým údajům. | Obsahuje {n} záznamů, které nemohou být stažen, kvůli rozbitým přístupovým údajům."
  filter:
    finished:
      title: Dokončeno
      ready: Ano
      unfinished: Ne
      all: Všechno
      working: Zpracovává se
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
    platforms: Platformy
    month: Stahovaný měsíc
</i18n>

<template>
  <v-container fluid>
    <v-row class="px-3">
      <v-col cols="auto">
        <v-select
          style="min-width: 220px"
          :items="filterFinishedList"
          v-model="filterFinished"
          :label="$t('filter.finished.title')"
        ></v-select>
      </v-col>
      <v-col cols="auto">
        <v-select
          style="min-width: 220px"
          :items="filterManualList"
          v-model="filterManual"
          :label="$t('filter.manual.title')"
        ></v-select>
      </v-col>
      <v-col cols="auto">
        <v-select
          style="min-width: 220px"
          :items="filterBrokenList"
          v-model="filterBroken"
          :label="$t('filter.broken.title')"
        ></v-select>
      </v-col>
      <v-col cols="2" class="month_input">
        <MonthEntry
          v-model="filterMonth"
          :label="$t('filter.month')"
          clearable
          :max-month="`${new Date()}`"
        ></MonthEntry>
      </v-col>
      <v-col cols="auto">
        <v-autocomplete
          style="min-width: 220px"
          :items="platformList"
          v-model="filterPlatforms"
          :label="$t('filter.platforms')"
          :loading="loadingPlatforms"
          return-object
          multiple
          closable-chips
          chips
          small-chips
          :item-title="(item) => item.short_name || item.name"
          item-value="pk"
          height="2.0rem"
        ></v-autocomplete>
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <v-data-table-server
          :items="tableData"
          :headers="headers"
          :loading="loading"
          v-model:items-per-page="itemsPerPage"
          v-model:page="page"
          :options="tableOptions"
          :items-length="totalCount"
          :must-sort="true"
          v-model:sort-by="tableOptions.sortBy"
        >
          <template v-slot:[`footer.prepend`]="">
            <v-btn
              size="x-small"
              variant="plain"
              elevation="2"
              @click="fetchHarvestsData()"
            >
              <v-icon size="x-small" class="pr-4">fas fa-sync-alt</v-icon>
              {{ $t("actions.refresh") }}
            </v-btn>
          </template>
          <template v-slot:[`item.pk`]="{ item }">
            <v-tooltip location="bottom">
              <template v-slot:activator="{ props }">
                <v-btn
                  variant="text"
                  size="small"
                  color="secondary"
                  @click.stop="
                    selectHarvest(item.pk);
                    showHarvestDialog = true;
                  "
                  v-bind="props"
                >
                  <v-icon left size="small">fas fa-external-link-alt</v-icon>
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
          <template v-slot:[`item.manual`]="{ item }">
            <CheckMark
              :true-tooltip="$t('tooltip.manual')"
              :false-tooltip="$t('tooltip.automatic')"
              :model-value="item.manual"
            ></CheckMark>
          </template>
          <template v-slot:[`item.created`]="{ item }">
            <div
              class="date_format"
              v-html="formatDateTime(item.created)"
            ></div>
          </template>
          <template v-slot:[`item.last_processed`]="{ item }">
            <div
              class="date_format"
              v-html="
                item.last_processed ? formatDateTime(item.last_processed) : '-'
              "
            ></div>
          </template>
          <template v-slot:[`item.month`]="{ item }">
            <span v-html="formatYM(item.start_date)"></span>
            <div v-if="formatYM(item.start_date) != formatYM(item.end_date)">
              <span v-html="' ' + formatYM(item.end_date)"></span>
            </div>
          </template>
          <template #[`item.lastAttempt`]="{ item }">
            <span v-if="item.finished || !item.lastAttempt">-</span>
            <div
              v-else
              class="date_format"
              v-html="formatDateTime(item.lastAttempt)"
            ></div>
          </template>
          <template #[`item.finishedRatio`]="{ item }">
            <v-icon size="x-small" v-if="item.working"
              >fa fa-cog fa-spin</v-icon
            >
            {{ item.finishedRatio }}
          </template>
        </v-data-table-server>
        <v-dialog
          v-model="showHarvestDialog"
          v-if="currentHarvestId"
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
                  :harvest-id="currentHarvestId"
                  ref="intentionsList"
                ></SushiFetchIntentionsListWidget>
              </div>
            </v-card-text>
            <v-card-actions>
              <v-spacer></v-spacer>
              <v-btn
                variant="elevated"
                color="defaultButton"
                @click="
                  showHarvestDialog = false;
                  currentHarvestId = null;
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
  isoDateTimeFormatSpans,
  parseDateTime,
  ymDateFormat,
} from "@/libs/dates";
import CheckMark from "@/components/util/CheckMark";
import MonthEntry from "@/components/util/MonthEntry";
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
    showOrganization: { default: false, type: Boolean },
    openHarvestId: { default: null, type: Number },
  },

  data() {
    return {
      harvestsData: [], // raw request data
      tableData: [], // processed data
      platformList: [],
      showHarvestDialog: !!this.openHarvestId,
      currentHarvestId: this.openHarvestId || null,
      loading: false,
      loadingPlatforms: false,
      filterFinished: "",
      filterManual: "",
      filterMonth: "",
      filterBroken: "",
      filterPlatforms: [],
      totalCount: 0,
      tableOptions: {
        sortBy: [{ key: "pk", order: "desc" }],
      },
      page: 1,
      itemsPerPage: 10,
    };
  },

  computed: {
    ...mapGetters({
      dateFnOptions: "dateFnOptions",
    }),
    harvestsUrl() {
      let finished = "";
      switch (this.filterFinished) {
        case "working":
          finished = "working";
          break;
        case "unfinished":
          finished = "no";
          break;
        case "ready":
          finished = "yes";
          break;
      }
      let platforms = "";
      if (this.filterPlatforms.length > 0) {
        platforms = this.filterPlatforms
          .map((platform) => platform.pk)
          .join(",");
      }
      let automatic = "";
      switch (this.filterManual) {
        case "automatic":
          automatic = "1";
          break;
        case "manual":
          automatic = "0";
          break;
      }
      let broken = "";
      switch (this.filterBroken) {
        case "yes":
          broken = "1";
          break;
        case "no":
          broken = "0";
          break;
      }
      // let month =
      //   typeof this.startDate === "object" &&
      //   this.startDate !== null &&
      //   "month" in this.startDate
      //     ? `${this.filterMonth.year}-${
      //         this.filterMonth.month <= 8
      //           ? `0${this.filterMonth.month + 1}`
      //           : this.filterMonth.month + 1
      //       }`
      //     : this.filterMonth || undefined;
      let month = null;
      if (
        typeof this.filterMonth === "object" &&
        this.filterMonth !== null &&
        "month" in this.filterMonth
      ) {
        month = `${this.filterMonth.year}-${
          this.filterMonth.month <= 8
            ? `0${this.filterMonth.month + 1}`
            : this.filterMonth.month + 1
        }`;
      } else if (
        typeof this.filterMonth === "string" &&
        this.filterMonth !== null
      ) {
        month = this.filterMonth;
      } else {
        month = this.filterMonth.year || undefined;
      }
      let sortBy = this.tableOptions.sortBy.length
        ? this.tableOptions.sortBy[0]
        : "";
      switch (sortBy.key) {
        case "finishedRatio":
          sortBy = [{ key: "finished", order: "desc" }];
          break;
        case "manual":
          sortBy = [{ key: "automatic", order: "desc" }];
          break;
        case "lastAttempt":
          sortBy = [{ key: "last_attempt_date", order: "desc" }];
          break;
        case "attempts":
          sortBy = [{ key: "attempt_count", order: "desc" }];
          break;
        case "month":
          sortBy = [{ key: "start_date", order: "desc" }];
          break;
      }
      return this.$router.resolve({
        path: "/api/scheduler/harvest/",
        query: {
          page: this.page,
          page_size: this.itemsPerPage,
          order_by: sortBy.key,
          desc: sortBy.order === "desc" ? true : false,
          finished,
          automatic,
          month,
          broken,
          platforms,
        },
      }).href;
    },
    headers() {
      const headersHead = [
        {
          title: "#",
          value: "pk",
          key: "pk",
          class: "wrap",
          sortable: true,
        },
      ];
      const headersTail = [
        {
          title: this.$t("title_fields.platforms"),
          value: "platforms",
          sortable: false,
        },
        {
          title: this.$t("table_header.created"),
          value: "created",
          key: "created",
          class: "wrap",
          sortable: true,
        },
        {
          title: this.$t("table_header.last_processed"),
          value: "last_processed",
          key: "last_processed",
          class: "wrap",
        },
        {
          title: this.$t("table_header.manual"),
          value: "manual",
          key: "manual",
          class: "wrap",
        },
        {
          title: this.$t("table_header.month"),
          value: "month",
          key: "start_date",
          class: "wrap",
        },
        {
          title: this.$t("table_header.finished"),
          value: "finishedRatio",
          key: "finishedRatio",
          align: "end",
        },
        {
          title: this.$t("table_header.attempts"),
          value: "attempts",
          key: "attempts",
          align: "end",
        },
        {
          title: this.$t("table_header.last_attempt"),
          value: "lastAttempt",
          key: "lastAttempt",
        },
      ];
      let headersMiddle = [];
      if (this.showOrganization) {
        headersMiddle.push({
          title: this.$t("title_fields.organizations"),
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
          title: this.$t("filter.finished.all"),
        },
        {
          value: "ready",
          title: this.$t("filter.finished.ready"),
        },
        {
          value: "unfinished",
          title: this.$t("filter.finished.unfinished"),
        },
        {
          value: "working",
          title: this.$t("filter.finished.working"),
        },
      ];
    },
    filterBrokenList() {
      return [
        {
          value: "",
          title: this.$t("filter.broken.all"),
        },
        {
          value: "yes",
          title: this.$t("filter.broken.yes"),
        },
        {
          value: "no",
          title: this.$t("filter.broken.no"),
        },
      ];
    },
    filterManualList() {
      return [
        {
          value: "",
          title: this.$t("filter.manual.all"),
        },
        {
          value: "automatic",
          title: this.$t("filter.manual.automatic"),
        },
        {
          value: "manual",
          title: this.$t("filter.manual.manual"),
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
      if (!result.error) {
        this.totalCount = result.response.data.count;
        this.harvestsData = result.response.data.results;
        this.dataToTable(result.response.data.results);
      }
      if (result.error !== "canceled") {
        // if the request was cancelled, it means another request was made
        // so we do not want to switch loading off
        this.loading = false;
      }
    },
    async selectHarvest(id) {
      const candidates = this.harvestsData.filter((item) => item.pk === id);
      if (candidates.length > 0) {
        this.currentHarvestId = candidates[0].pk;
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
          working: rec.stats.working > 0,
        });
      }
      this.tableData = res;
    },
    formatDateTime(value) {
      return isoDateTimeFormatSpans(value);
    },
    formatYM(value) {
      if (value) {
        return ymDateFormat(parseDateTime(value));
      }
      return "-";
    },
    async fetchPlatforms() {
      this.platformList = [];
      this.loadingPlatforms = true;
      let result = await this.http({
        url: "/api/organization/-1/all-platform/",
      });
      this.loadingPlatforms = false;
      if (!result.error) {
        this.platformList = result.response.data;
        this.platformList.sort((a, b) => {
          let atext = a.short_name || a.name;
          let btext = b.short_name || b.short_name;
          return atext.localeCompare(btext);
        });
      }
    },
  },

  mounted() {
    this.fetchHarvestsData();
    this.fetchPlatforms();
  },

  watch: {
    harvestsUrl() {
      this.fetchHarvestsData();
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

<style>
.v-data-table-footer__items-per-page {
  margin-left: auto;
}
.month_input {
  min-width: 170px;
}

.date_format {
  min-width: 71px;
}
</style>
