<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml" src="@/locales/sushi.yaml"></i18n>
<i18n lang="yaml">
en:
  currently_downloading: There are no data yet, please wait until the download finishes. It can take from seconds to minutes.
  planned_to_download: Fetching of data was planned, but attempt hasn't been executed yet.
  planned_for_retry: "Based on result of previous attempt, later retry was planned. The new attempt is planned for {date}. "
  attempt_deleted: Download was executed but information about the download were deleted.
  future_start_info: Harvesting is currently waiting for free slot in the download queue.
  finished_filter: Filter by finished
  finished: Finished only
  unfinished: Unfinished only
  all: All
  broken_credentials_hint: You can fix the credentials on the {link} page. This link automatically applies filter limiting displayed credentials to only the broken ones.
  progress: Finished
  stats: Statistics
  status: Status
  previous_attempt: Previous attempt

cs:
  currently_downloading: Data ještě nejsou k dispozici - vyčkejte prosím, až budou stáhnutá. Může to trvat od sekund po jednotky minut.
  planned_to_download: Stahování dat bylo naplánováno, ale zatím nebylo provedeno.
  planned_for_retry: "Na základě předchozího pokusu bylo naplánováno pozdější stažení. Nový pokus je naplánovaný na {date}. "
  attempt_deleted: Stahování proběhlo, ale informace o stahování byly smazány.
  future_start_info: Stahování aktuálně čeká na uvolnění místa ve frontě.
  finished_filter: Filtr podle dokončení
  finished: Pouze dokončené
  unfinished: Pouze nedokončené
  all: Všechny
  broken_credentials_hint: Přihlašovací údaje můžete opravit na stránce {link}. Tento odkaz automaticky zapne filtr, který zobrazí jen problematické přihlašovací údaje.
  progress: Dokončeno
  stats: Statistika
  status: Stav
  previous_attempt: Předchozí pokus
</i18n>
<template>
  <v-container fluid class="pt-0 pb-0">
    <v-row>
      <v-col>
        <v-data-table
          :items="filteredItems"
          :headers="headers"
          :expanded.sync="expanded"
          show-expand
          item-key="pk"
          expand-icon="fa fa-caret-down"
          :loading="loading"
          dense
        >
          <template #top>
            <v-container fluid class="pa-0">
              <v-row>
                <v-col
                  v-if="totalCount > 0"
                  cols="6"
                  sm="4"
                  lg="3"
                  class=""
                  align-self="center"
                >
                  <v-progress-linear
                    :value="(100 * finishedCount) / totalCount"
                    height="1.5rem"
                    color="blue lighten-2"
                  >
                    {{ $t("progress") }}: {{ finishedCount }} / {{ totalCount }}
                  </v-progress-linear>
                </v-col>

                <v-col align-self="center">
                  {{ $t("stats") }}:
                  <v-tooltip
                    bottom
                    v-for="rec in statusCounts"
                    :key="rec.state"
                  >
                    <template #activator="{ on }">
                      <span
                        class="mr-3 clickable"
                        v-on="on"
                        @click="switchStateFilter(rec.state)"
                        :class="
                          stateFilter !== null && stateFilter !== rec.state
                            ? 'alpha'
                            : ''
                        "
                      >
                        <v-icon :color="rec.icon.color">
                          {{ rec.icon.icon }}
                        </v-icon>
                        {{ rec.count }}
                      </span>
                    </template>
                    {{ $t("sushi.state_desc." + rec.state) }}
                  </v-tooltip>
                </v-col>

                <v-col cols="6" sm="4" lg="3">
                  <v-select
                    :label="$t('finished_filter')"
                    :items="finishedFilterItems"
                    v-model="finishedFilter"
                  ></v-select>
                </v-col>
              </v-row>
            </v-container>
          </template>

          <template #item.status="{ item }">
            <FetchIntentionStatusIcon :fetch-intention="item" />
          </template>

          <template #item.isFinished="{ item }">
            <CheckMark :value="item.isFinished" />
          </template>

          <template #expanded-item="{ headers, item }">
            <td></td>
            <td :colspan="headers.length - 1" class="py-2">
              <span
                v-if="item.fetchingData"
                v-text="$t('currently_downloading')"
              ></span>
              <span
                v-else-if="item.attemptDeleted"
                v-text="$t('attempt_deleted')"
              ></span>
              <div v-else-if="item.attempt">
                <div v-if="item.attempt && item.attempt.data_file">
                  <strong>{{ $t("title_fields.data_file") }}</strong
                  >:
                  <a :href="item.attempt.data_file" target="_blank">{{
                    item.attempt.data_file
                  }}</a>
                </div>
                <div v-if="item.attempt && item.attempt.error_code">
                  <strong>{{ $t("title_fields.error_code") }}</strong
                  >: {{ item.attempt.error_code }}
                </div>
                <div v-if="item.attempt && item.attempt.log">
                  <strong>{{ $t("title_fields.log") }}</strong
                  >: {{ item.attempt.log }}
                </div>
              </div>

              <span v-else-if="item.brokenCredentials">
                <i18n path="broken_credentials_hint">
                  <template #link>
                    <router-link
                      :to="{
                        name: 'sushi-credentials-list',
                        query: { broken: 1 },
                      }"
                      >{{ $t("pages.sushi_management") }}</router-link
                    >
                  </template>
                </i18n>
              </span>

              <span v-else>
                <i18n
                  :path="
                    item.isRetry ? 'planned_for_retry' : 'planned_to_download'
                  "
                  tag="span"
                >
                  <template #date>{{ notBeforeHuman(item) }}</template>
                </i18n>
                <span
                  v-if="!futureStart"
                  v-text="$t('future_start_info')"
                ></span>
                <div v-if="item.previousAttempt">
                  <br />
                  <strong>{{ $t("previous_attempt") }}:</strong>
                  <ul>
                    <li v-if="item.previousAttempt.error_code">
                      <strong>{{ $t("title_fields.error_code") }}</strong
                      >: {{ item.previousAttempt.error_code }}
                    </li>
                    <li v-if="item.previousAttempt.log">
                      <strong>{{ $t("title_fields.log") }}</strong
                      >: {{ item.previousAttempt.log }}
                    </li>
                  </ul>
                </div>
              </span>
            </td>
          </template>
        </v-data-table>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { mapActions, mapGetters, mapState } from "vuex";
import axios from "axios";
import formatDistanceToNowStrict from "date-fns/formatDistanceToNowStrict";
import isFuture from "date-fns/isFuture";
import differenceInMilliseconds from "date-fns/differenceInMilliseconds";
import formatRelative from "date-fns/formatRelative";
import intervalToDuration from "date-fns/intervalToDuration";
import formatDuration from "date-fns/formatDuration";
import FetchIntentionStatusIcon from "@/components/sushi/FetchIntentionStatusIcon";
import { annotateIntention } from "@/libs/intention-state";
import CheckMark from "@/components/util/CheckMark";
import { intentionStateToIcon } from "@/libs/intention-state";
import Color from "color";

export default {
  name: "SushiFetchIntentionsListWidget",
  components: { CheckMark, FetchIntentionStatusIcon },
  props: {
    harvestId: {
      required: false,
      type: Number,
      default: null,
    },
    retryInterval: { default: 3000, type: Number },
    showOrganization: { default: false, type: Boolean },
    showPlatform: { default: false, type: Boolean },
  },

  data() {
    return {
      loading: false,
      intentionData: [],
      startTime: null,
      now: null,
      lastCheck: null,
      inactive: false,
      harvestData: null,
      expanded: [],
      finishedFilter: "all",
      finishedFilterItems: [
        { value: "all", text: this.$i18n.t("all") },
        { value: "unfinished", text: this.$i18n.t("unfinished") },
        { value: "finished", text: this.$i18n.t("finished") },
      ],
      stateFilter: null,
    };
  },

  computed: {
    ...mapState({
      currentLocale: "appLanguage",
    }),
    ...mapGetters({
      dateFnOptions: "dateFnOptions",
    }),
    intentionsUrl() {
      if (this.harvestId) {
        return `/api/scheduler/harvest/${this.harvestId}/intention/`;
      }
      return null;
    },
    headers() {
      return [
        {
          text: this.$t("labels.platform"),
          value: "platform_name",
        },
        {
          text: this.$t("organization"),
          value: "organization_name",
        },
        {
          text: this.$t("labels.report_type"),
          value: "counter_report_code",
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
          text: this.$t("labels.finished"),
          value: "isFinished",
        },
        {
          text: this.$t("status"),
          value: "status",
          sortable: false,
        },
      ];
    },
    retryTimeout() {
      let timeouts = [];
      this.intentionData.forEach((intention) => {
        if (!intention.isFinished && !intention.brokenCredentials) {
          if (intention.notBefore) {
            const diff = differenceInMilliseconds(
              intention.notBefore,
              this.now
            );
            timeouts.push(
              diff > this.retryInterval ? diff : this.retryInterval
            );
          } else {
            timeouts.push(this.retryInterval);
          }
        }
      });
      if (timeouts.length > 0) {
        return timeouts.sort()[0];
      }
      return null;
    },
    filteredItems() {
      return this.intentionData
        .filter((item) => {
          if (this.finishedFilter === "all") {
            return true;
          } else if (this.finishedFilter === "finished") {
            return item.isFinished;
          } else {
            return !item.isFinished;
          }
        })
        .filter(
          (item) => this.stateFilter === null || this.stateFilter === item.state
        );
    },
    finishedCount() {
      return this.intentionData.filter((item) => item.isFinished).length;
    },
    totalCount() {
      return this.intentionData.length;
    },
    statusCounts() {
      let counts = new Map();
      this.intentionData.forEach((item) => {
        if (counts.has(item.state)) {
          counts.set(item.state, counts.get(item.state) + 1);
        } else {
          counts.set(item.state, 1);
        }
      });
      let out = [];
      for (let [state, count] of counts.entries()) {
        out.push({
          state: state,
          count: count,
          icon: intentionStateToIcon(state),
        });
      }
      out.sort((a, b) => (a.count > b.count ? -1 : 1));
      return out;
    },
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    async fetchIntentions(showLoader = true) {
      if (!this.intentionsUrl) {
        return;
      }
      if (showLoader) {
        this.loading = true;
      }
      try {
        let response = await axios.get(this.intentionsUrl);
        this.intentionData = response.data;
        this.intentionData.forEach(annotateIntention);
      } catch (error) {
        this.showSnackbar({
          content: "Error fetching harvest data: " + error,
          color: "error",
        });
      } finally {
        this.loading = false;
      }
    },
    stop() {
      this.inactive = true;
    },
    elapsedTime(intention) {
      const duration = intervalToDuration({
        start: intention.notBefore,
        end: this.now,
      });
      return formatDuration(duration, this.dateFnOptions);
    },
    tilStart(intention) {
      return formatDistanceToNowStrict(intention.notBefore, this.dateFnOptions);
    },
    futureStart(intention) {
      return isFuture(intention.notBefore) && !intention.isDuplicate;
    },
    notBeforeHuman(intention) {
      if (intention.notBefore) {
        return formatRelative(
          intention.notBefore,
          this.now,
          this.dateFnOptions
        );
      }
      return "-";
    },
    async scheduleRecheck(showLoader = true) {
      // showLoader is used to only show loader on the first load, but not when doing updates later on
      await this.fetchIntentions(showLoader);
      console.log("retry timeout:", this.retryTimeout);

      if (!this.inactive && this.retryTimeout) {
        // setTimeout delay (ms) can't be greater than 32bit integer
        setTimeout(() => this.scheduleRecheck(false), Math.min(1000 * 60 * 60, this.retryTimeout));
      }
    },
    switchStateFilter(state) {
      if (this.stateFilter === state) {
        this.stateFilter = null;
      } else {
        this.stateFilter = state;
      }
    },
  },

  watch: {
    intentionsUrl() {
      this.scheduleRecheck();
    },
  },

  created() {
    this.startTime = new Date();
    this.now = new Date();
  },

  mounted() {
    this.scheduleRecheck();
    setInterval(() => {
      this.now = new Date();
    }, 250);
  },
  beforeDestroy() {
    this.inactive = true;
  },
};
</script>

<style scoped lang="scss">
.clickable {
  cursor: pointer;
}
.alpha {
  opacity: 0.3;
}
</style>
