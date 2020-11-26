<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml">
en:
  table_header:
    created: Created
    manual: Manually created
    finished: Finished
    last_attempt: Finish planned
  downloads: Downloads
  tooltip:
    automatic: Automatically planned harvesting.
    manual: Manually planned harvesting.
  filter:
    finished:
      title: Finished
      ready: Yes
      working: No
      all: All

cs:
  table_header:
    created: Vytvořeno
    manual: Manuálně vytvořeno
    finished: Hotovo
    last_attempt: Dokončení plánováno
  downloads: Stahování
  tooltip:
    automatic: Automaticky naplánované stahování.
    manual: Manuálně naplánované stahování.
  filter:
    finished:
      title: Dokončeno
      ready: Ano
      working: Ne
      all: Všechno
</i18n>

<template>
  <v-container>
    <v-row class="px-3">
      <v-col cols="auto">
        <v-select
          :items="filterFinishedList"
          v-model="filterFinished"
          :label="$t('filter.finished.title')"
        ></v-select>
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
            <v-btn
              text
              small
              color="secondary"
              @click.stop="
                fetchHarvestData(item.pk);
                showHarvestDialog = true;
              "
            >
              <v-icon left small>fa-external-link-alt</v-icon>
              <span>{{ item.pk }}</span>
            </v-btn>
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
          <template #item.lastAttempt="{ item }">
            <span v-if="item.finished">-</span>
            <v-tooltip bottom v-else>
              <template #activator="{ on }">
                <span
                  v-html="formatDateTimeRelative(item.lastAttempt)"
                  v-on="on"
                ></span>
              </template>
              <span v-html="formatDateTimePlain(item.lastAttempt)"></span>
            </v-tooltip>
          </template>
        </v-data-table>

        <v-dialog v-model="showHarvestDialog" v-if="currentHarvest">
          <v-card>
            <v-card-text class="pb-0">
              <v-row>
                <v-col>
                  <h3 class="pt-3 text-h5">{{ $t("downloads") }}</h3>
                </v-col>
              </v-row>
              <div class="pt-5">
                <v-expansion-panels>
                  <FetchIntentionStatusWidget
                    v-for="intention in currentHarvest.intentions"
                    :intention-id="intention.pk"
                    :harvest-id="currentHarvest.pk"
                    :key="intention.pk"
                    :retryInterval="retryInterval"
                    :show-organization="showOrganization"
                    :show-platform="showPlatform"
                    :initialIntentionData="intention"
                    clearable
                  >
                  </FetchIntentionStatusWidget>
                </v-expansion-panels>
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
import axios from "axios";
import { mapActions, mapGetters, mapState } from "vuex";
import {
  isoDateTimeFormat,
  isoDateTimeFormatSpans,
  parseDateTime,
} from "@/libs/dates";
import CheckMark from "@/components/util/CheckMark";
import formatRelative from "date-fns/formatRelative";
import FetchIntentionStatusWidget from "@/components/sushi/FetchIntentionStatusWidget";

export default {
  name: "HarvestsTable",

  components: {
    FetchIntentionStatusWidget,
    CheckMark,
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
      loadingHarvest: false,
      filterFinished: "",
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
      let sortBy = this.tableOptions.sortBy ? this.tableOptions.sortBy[0] : "";
      let sortDesc = this.tableOptions.sortDesc
        ? this.tableOptions.sortDesc[0]
        : false;
      if (sortBy === "finishedRatio") {
        sortBy = "finished";
      } else if (sortBy === "manual") {
        sortBy = "automatic";
        sortDesc = !sortDesc;
      } else if (sortBy === "lastAttempt") {
        sortBy = "last_attempt_date";
      }
      return `/api/scheduler/harvest/?page=${this.tableOptions.page}&page_size=${this.tableOptions.itemsPerPage}&order_by=${sortBy}&desc=${sortDesc}${filterFinished}`;
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
          text: this.$t("table_header.manual"),
          value: "manual",
          class: "wrap",
        },
        {
          text: this.$t("table_header.finished"),
          value: "finishedRatio",
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
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    async fetchHarvestsData() {
      this.loading = true;
      try {
        let result = await axios.get(this.harvestsUrl);
        this.totalCount = result.data.count;
        this.harvestsData = result.data.results;
        this.dataToTable(result.data.results);
        this.lastFetchedTime = new Date();
      } catch (error) {
        this.showSnackbar({
          content: "Error getting harvest list " + error,
          color: "error",
        });
      } finally {
        this.loading = false;
      }
    },
    async fetchHarvestData(id) {
      this.loadingHarvest = true;
      try {
        let result = await axios.get(`/api/scheduler/harvest/${id}/`);
        this.currentHarvest = result.data;
      } catch (error) {
        this.showSnackbar({
          content: "Error getting harvest " + error,
          color: "error",
        });
      } finally {
        this.loadingHarvest = false;
      }
    },
    dataToTable(harvests) {
      let res = [];
      for (let rec of harvests) {
        res.push({
          pk: rec.pk,
          created: rec.created,
          manual: rec.automatic === null,
          finished: rec.stats.total === rec.stats.planned,
          finishedRatio: `${rec.stats.total - rec.stats.planned}/${
            rec.stats.total
          }`,
          organizations: rec.organizations
            .map((item) => item.short_name)
            .join(", "),
          platforms: rec.platforms.map((item) => item.short_name).join(", "),
          lastAttempt: parseDateTime(rec.last_attempt_date),
        });
      }
      this.tableData = res;
    },
    formatDateTime(value) {
      return isoDateTimeFormatSpans(value);
    },
    formatDateTimePlain(value) {
      return isoDateTimeFormat(value);
    },
    formatDateTimeRelative(value) {
      return formatRelative(value, this.now, this.dateFnOptions);
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
        this.lastFetchTimer = setTimeout(
            () => {
                this.fetchHarvestsData();
            },
            this.refreshInterval,
        )
    },
    showHarvestDialog() {
      if (!this.showHarvestDialog) {
        this.currentHarvest = null;
        this.fetchHarvestsData();
      }
    },
  },
};
</script>
