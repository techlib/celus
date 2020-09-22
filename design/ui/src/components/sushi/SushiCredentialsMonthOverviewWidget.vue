<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml">
en:
  hide_successful: Hide successful rows
  stats: Statistics
  no_data_yet: No attempts were made for the selected month
  show_inactive: Show inactive
  show_inactive_tooltip: Also shows credentials that are not automatically harvested
  enabled: Automatically harvested
  not_enabled: Not automatically harvested

cs:
  hide_successful: Skrýt úspěšné řádky
  stats: Statistika
  no_data_yet: Pro vybraný měsíc nebyla zatím stažena žádná data
  show_inactive: Zobrazit neaktivní
  show_inactive_tooltip: Zobrazí také přihlašovací údaje, pro které nejsou data automaticky stahována
  enabled: Automaticky stahováno
  not_enabled: Není automaticky stahováno
</i18n>

<template>
  <v-card>
    <v-card-text>
      <v-container fluid>
        <v-row>
          <v-col cols="6" sm="4" md="3" lg="2">
            <v-menu
              v-model="showMonthMenu"
              transition="scale-transition"
              offset-y
            >
              <template v-slot:activator="{ on }">
                <v-text-field
                  v-model="selectedMonth"
                  :label="$t('month')"
                  prepend-icon="fa-calendar"
                  readonly
                  v-on="on"
                >
                  <template #prepend-inner>
                    <IconButton @click="shiftMonth(-1)"
                      >fa-caret-left</IconButton
                    >
                  </template>
                  <template #append>
                    <IconButton
                      @click="shiftMonth(1)"
                      :disabled="selectedMonth >= lastMonth"
                      >fa-caret-right</IconButton
                    >
                  </template>
                </v-text-field>
              </template>
              <v-date-picker
                v-model="selectedMonth"
                type="month"
                no-title
                :locale="$i18n.locale"
                :allowed-dates="allowedMonths"
              ></v-date-picker>
            </v-menu>
          </v-col>
          <v-col cols="6" sm="4" md="3" lg="2" xl="1">
            <v-select
              :items="[
                { text: '4 + 5', value: null },
                { text: '4', value: 4 },
                { text: '5', value: 5 },
              ]"
              v-model="counterVersion"
              :label="$t('labels.counter_version')"
              class="short"
            ></v-select>
          </v-col>
          <v-col cols="12" sm="6" md="4" lg="3">
            <v-select
              :label="$t('platform')"
              v-model="selectedPlatform"
              :items="usedPlatforms"
              item-value="pk"
              item-text="name"
            >
            </v-select>
          </v-col>
          <v-col cols="6" md="auto">
            <v-switch v-model="hideSuccessful" :label="$t('hide_successful')">
            </v-switch>
          </v-col>
          <v-col cols="6" md="auto">
            <v-tooltip bottom>
              <template #activator="{ on }">
                <span v-on="on">
                  <v-switch v-model="showInactive" :label="$t('show_inactive')">
                  </v-switch>
                </span>
              </template>
              {{ $t("show_inactive_tooltip") }}
            </v-tooltip>
          </v-col>
        </v-row>

        <v-row>
          <v-col>
            <div class="stats">
              <h4 class="d-inline-block mr-5">{{ $t("stats") }}:</h4>
              <span v-if="stateStats.length">
                <span
                  v-for="[state, count] in stateStats"
                  class="mr-3"
                  :key="state"
                >
                  <SushiAttemptStateIcon :force-state="state" />
                  {{ count }}
                </span>
              </span>
              <span v-else v-text="$t('no_data_yet')"></span>
            </div>
          </v-col>
        </v-row>

        <v-row>
          <v-data-table
            :items="sushiCredentialsWithAttempts"
            :headers="headers"
            :search="search"
            :items-per-page.sync="itemsPerPage"
            :sort-by="orderBy"
            multi-sort
            :footer-props="{ itemsPerPageOptions: [10, 25, 50, 100] }"
            :loading="loading"
            dense
          >
            <template
              v-for="rt in usedReportTypes"
              v-slot:[slotName(rt)]="{ item }"
            >
              <span
                :key="`${rt.code}-${item.credentials_id}`"
                @click="
                  (item[rt.code] &&
                    item[rt.code].pk &&
                    showAttempt(item[rt.code])) ||
                    null
                "
                :class="{ clickable: item[rt.code] && item[rt.code].pk }"
              >
                <SushiAttemptStateIcon :attempt="item[rt.code]" latest />
              </span>
            </template>
            <template #item.counter_version="{ item }">
              <v-tooltip bottom>
                <template #activator="{ on }">
                  <span
                    class="pl-5"
                    :class="item.enabled ? '' : 'red--text'"
                    v-on="on"
                  >
                    <v-icon v-if="!item.enabled" x-small>fa fa-unlink</v-icon>
                    {{ item.counter_version }}
                  </span>
                </template>
                <span v-if="item.enabled" v-text="$t('enabled')"></span>
                <span v-else v-text="$t('not_enabled')"></span>
              </v-tooltip>
            </template>
          </v-data-table>
        </v-row>
      </v-container>
    </v-card-text>

    <v-dialog v-model="showDetailsDialog">
      <SushiAttemptListWidget
        v-if="selectedAttempt"
        :attempt-id="selectedAttempt.pk"
        @close="closeDetailsDialog"
        ref="attemptListWidget"
      >
      </SushiAttemptListWidget>
    </v-dialog>
  </v-card>
</template>

<script>
import axios from "axios";
import { mapActions, mapGetters } from "vuex";
import debounce from "lodash/debounce";
import SushiAttemptListWidget from "@/components/sushi/SushiAttemptListWidget";
import startOfMonth from "date-fns/startOfMonth";
import addDays from "date-fns/addDays";
import addMonths from "date-fns/addMonths";
import { parseDateTime, ymDateFormat } from "@/libs/dates";
import SushiAttemptStateIcon from "@/components/sushi/SushiAttemptStateIcon";
import {
  attemptState,
  ATTEMPT_SUCCESS,
  ATTEMPT_NOT_MADE,
} from "@/libs/attempt-state";
import IconButton from "@/components/sushi/IconButton";

export default {
  name: "SushiCredentialsMonthOverviewWidget",

  components: { IconButton, SushiAttemptStateIcon, SushiAttemptListWidget },

  props: {
    dialogMaxWidth: {
      required: false,
      default: "1000px",
    },
    organizationId: {
      default: -1,
      type: Number,
      required: false,
    },
  },

  data() {
    return {
      sushiCredentialsList: [],
      attemptData: [],
      attemptMap: new Map(),
      reportTypes: [],
      search: "",
      itemsPerPage: 25,
      selectedAttempt: null,
      showDetailsDialog: false,
      orderBy: ["platform.name", "organization.name"],
      loading: false,
      selectedMonth:
        this.$route.query.month ||
        ymDateFormat(addDays(startOfMonth(new Date()), -15)),
      showMonthMenu: false,
      counterVersion: null,
      hideSuccessful: false,
      selectedPlatform: null,
      showInactive: false,
    };
  },
  computed: {
    ...mapGetters({
      consortialInstall: "consortialInstall",
    }),
    headers() {
      let allHeaders = [
        {
          text: this.$i18n.t("title"),
          value: "title",
          class: "wrap",
        },
        {
          text: this.$i18n.t("platform"),
          value: "platform.name",
        },
        {
          text: this.$i18n.t("organization"),
          value: "organization.name",
          class: "wrap",
        },
        {
          text: this.$i18n.t("title_fields.counter_version"),
          value: "counter_version",
          align: "end",
        },
      ];
      for (let reportType of this.usedReportTypes) {
        allHeaders.push({
          text: reportType.code,
          value: reportType.code,
          sortable: false,
        });
      }
      return allHeaders.filter(
        (row) => row.value !== "outside_consortium" || this.consortialInstall
      );
    },
    searchDebounced: {
      get() {
        return this.search;
      },
      set: debounce(function (value) {
        this.search = value;
      }, 500),
    },
    credentialsUrl() {
      return `/api/sushi-credentials/?organization=${this.organizationId}`;
    },
    attemptsUrl() {
      if (!this.selectedMonth) {
        return null;
      }
      let url = `/api/sushi-credentials/month-overview/?organization=${this.organizationId}&month=${this.selectedMonth}`;
      if (this.showInactive) {
        url += "&disabled=true";
      }
      return url;
    },
    usedReportTypes() {
      let usedRTIds = new Set();
      for (let cred of this.sushiCredentialsWithAttempts) {
        for (let rt of cred.active_counter_reports) {
          usedRTIds.add(rt);
        }
      }
      return this.reportTypes.filter((item) => usedRTIds.has(item.id));
    },
    usedPlatforms() {
      let usedPlatforms = new Set(
        this.sushiCredentialsList
          .filter(
            (item) =>
              this.counterVersion === null ||
              item.counter_version === this.counterVersion
          )
          .map((item) => item.platform)
      );
      return [{ name: "-", pk: null }, ...usedPlatforms].sort(
        (a, b) => a.name > b.name
      );
    },
    activeAttempts() {
      let attempts = [];
      for (let cred of this.sushiCredentialsWithAttempts) {
        for (let rt of cred.active_counter_reports_long) {
          if (cred.hasOwnProperty(rt.code)) {
            attempts.push(cred[rt.code]);
          }
        }
      }
      return attempts;

      let activeCredentials = new Set(
        this.sushiCredentialsWithAttempts.map((item) => item.pk)
      );
      return this.attemptData.filter((item) =>
        activeCredentials.has(item.credentials_id)
      );
    },
    allSushiCredentialsWithAttempts() {
      return this.sushiCredentialsList.map((item) => {
        for (let reportType of item.active_counter_reports_long) {
          let key = `${item.pk}-${reportType.id}`;
          if (this.attemptMap.has(key)) {
            item[reportType.code] = this.attemptMap.get(key);
          } else {
            item[reportType.code] = { untried: true, state: ATTEMPT_NOT_MADE };
          }
        }
        return item;
      });
    },
    sushiCredentialsWithAttempts() {
      let list = this.allSushiCredentialsWithAttempts
        .filter((item) => this.showInactive || item.enabled)
        .filter(
          (item) =>
            this.counterVersion === null ||
            item.counter_version === this.counterVersion
        )
        .filter(
          (item) =>
            this.selectedPlatform === null ||
            item.platform.pk === this.selectedPlatform
        );
      if (this.hideSuccessful) {
        list = list.filter(
          (item) =>
            item.active_counter_reports_long.filter(
              (rt) => item[rt.code] && item[rt.code].state === ATTEMPT_SUCCESS
            ).length != item.active_counter_reports_long.length
        );
      }
      return list;
    },
    stateStats() {
      let stats = new Map();
      for (let state of this.activeAttempts.map((attempt) => attempt.state)) {
        if (stats.has(state)) {
          stats.set(state, stats.get(state) + 1);
        } else {
          stats.set(state, 1);
        }
      }
      return [...stats.entries()];
    },
    lastMonth() {
      return ymDateFormat(addDays(startOfMonth(new Date()), -15));
    },
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    async loadSushiCredentialsList() {
      this.loading = true;
      try {
        let response = await axios.get(this.credentialsUrl);
        this.sushiCredentialsList = response.data;
      } catch (error) {
        this.showSnackbar({
          content: "Error loading credentials list: " + error,
          color: "error",
        });
      } finally {
        this.loading = false;
      }
    },
    async loadAttempts() {
      if (!this.attemptsUrl) {
        return;
      }
      this.loading = true;
      try {
        let response = await axios.get(this.attemptsUrl);
        this.attemptData = response.data;
        // create a map to easily find the attempt data
        let attemptMap = new Map();
        this.attemptData.forEach((item) => (item.state = attemptState(item)));
        this.attemptData.forEach((item) =>
          attemptMap.set(
            `${item.credentials_id}-${item.counter_report_id}`,
            item
          )
        );
        this.attemptMap = attemptMap;
      } catch (error) {
        this.showSnackbar({
          content: "Error loading attempts: " + error,
          color: "error",
        });
      } finally {
        this.loading = false;
      }
    },
    async loadReportTypes() {
      this.loading = true;
      try {
        let response = await axios.get("/api/counter-report-type/");
        this.reportTypes = response.data;
      } catch (error) {
        this.showSnackbar({
          content: "Error loading report types: " + error,
          color: "error",
        });
      } finally {
        this.loading = false;
      }
    },
    closeDetailsDialog() {
      this.selectedCredentials = null;
      this.$refs["attemptListWidget"].cleanup();
      this.selectedAttempt = null;
      this.showDetailsDialog = false;
    },
    allowedMonths(value) {
      let now = ymDateFormat(new Date());
      return value <= now;
    },
    slotName: (rt) => "item." + rt.code,
    showAttempt(attempt) {
      this.selectedAttempt = attempt;
      this.showDetailsDialog = true;
    },
    shiftMonth(months) {
      let date = parseDateTime(this.selectedMonth);
      const shifted = ymDateFormat(addMonths(date, months));
      if (this.allowedMonths(shifted)) {
        this.selectedMonth = shifted;
      }
    },
  },

  watch: {
    selectedMonth() {
      history.pushState(
        {},
        null,
        this.$route.path + `?month=${this.selectedMonth}`
      );
    },
    dataUrl() {
      this.loadSushiCredentialsList();
    },
    attemptsUrl() {
      this.loadAttempts();
    },
  },

  mounted() {
    this.loadReportTypes();
    this.loadSushiCredentialsList();
    this.loadAttempts();
  },
};
</script>

<style lang="scss" scoped>
div.stats {
  background-color: #efefef;
  padding: 0.5rem 1rem;
  border-radius: 5px;
}

.clickable {
  cursor: pointer;
}
</style>
