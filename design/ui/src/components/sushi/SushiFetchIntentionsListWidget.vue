<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml" src="@/locales/sushi.yaml"></i18n>
<i18n lang="yaml">
en:
  currently_downloading: There are no data yet, please wait until the download finishes. It can take from seconds to minutes.
  planned_to_download: "Fetching of data was planned for {date}, but attempt hasn't been executed yet."
  planned_for_retry: "Based on result of previous attempt, later retry was planned. The new attempt is planned for {date}. "
  attempt_deleted: Download was executed but information about the download were deleted.
  attempt_canceled: Download was canceled.
  future_start_info: Harvesting is currently waiting for free slot in the download queue.
  finished_filter: Filter by finished
  finished: Finished only
  unfinished: Unfinished only
  all: All
  broken_credentials_hint: You can fix the credentials on the {link} page. This link automatically applies filter limiting displayed credentials to only the broken ones.
  progress: Finished
  stats: Statistics
  status: Status
  actions_force_run: Reschedule and start download right now.
  actions_cancel: Cancel download.
  actions_cancel_title: Cancel
  actions_force_run_title: Run
  previous_attempt: Previous attempt
  not_before_tooltip: Data might not be avialable or some ratelimit was reached.
  runnable:
    all: All
    filter: Ready to run
    now: Immediately
    future: In the future
    never: Can't be run

cs:
  currently_downloading: Data ještě nejsou k dispozici - vyčkejte prosím, až budou stáhnutá. Může to trvat od sekund po jednotky minut.
  planned_to_download: "Stahování dat bylo naplánováno na {date}, ale zatím nebylo provedeno."
  planned_for_retry: "Na základě předchozího pokusu bylo naplánováno pozdější stažení. Nový pokus je naplánovaný na {date}. "
  attempt_deleted: Stahování proběhlo, ale informace o stahování byly smazány.
  attempt_canceled: Stahování bylo zrušeno.
  future_start_info: Stahování aktuálně čeká na uvolnění místa ve frontě.
  finished_filter: Filtr podle dokončení
  finished: Pouze dokončené
  unfinished: Pouze nedokončené
  all: Všechny
  broken_credentials_hint: Přihlašovací údaje můžete opravit na stránce {link}. Tento odkaz automaticky zapne filtr, který zobrazí jen problematické přihlašovací údaje.
  progress: Dokončeno
  stats: Statistika
  status: Stav
  actions: Akce
  actions_force_run: Přeplánovat a spustit stahování hned.
  actions_cancel: Zrušit stahování.
  actions_cancel_title: Zrušit
  actions_force_run_title: Spustit
  previous_attempt: Předchozí pokus
  not_before_tooltip: Data nemusí být dostupná nebo byl překročen limit stažení.
  runnable:
    all: Všechno
    filter: Připraveno ke spuštění
    now: Hned
    future: V budoucnu
    never: Nelze pustit
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
          <template
            v-for="h in headers"
            v-slot:[`header.${h.value}`]="{ header }"
          >
            <v-tooltip bottom v-if="header.tooltip">
              <template v-slot:activator="{ on }">
                <span v-on="on">{{ h.text }}</span>
              </template>
              <span>{{ h.tooltip }}</span>
            </v-tooltip>
            <span v-else>{{ h.text }}</span>
          </template>

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
                    <v-progress-circular
                      v-if="retryTimeout"
                      size="16"
                      color="#000044"
                      width="2"
                      indeterminate
                      class="mr-2"
                    />
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
                <v-col cols="6" sm="4" lg="3">
                  <v-select
                    :label="$t('runnable.filter')"
                    :items="runnableFilterItems"
                    v-model="runnableFilter"
                  ></v-select>
                </v-col>
              </v-row>
            </v-container>
          </template>

          <template v-slot:item.notBefore="{ item }">
            <span
              v-html="formatDateTime(item.notBefore)"
              v-if="!item.isFinished"
            ></span>
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
                v-else-if="item.isCanceled"
                v-text="$t('attempt_canceled')"
              ></span>
              <span
                v-else-if="item.attemptDeleted"
                v-text="$t('attempt_deleted')"
              ></span>
              <div v-else-if="item.attempt">
                <AttemptExtractedData :attempt="item.attempt" />
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
              <div v-if="item.isForceRunPossible || item.isCancelPossible">
                <br />
              </div>
              <v-tooltip bottom>
                <template #activator="{ on }">
                  <v-btn
                    v-if="item.isForceRunPossible"
                    text
                    small
                    v-on="on"
                    @click="forceRun(item)"
                    :loading="loadingActions.trigger.includes(item.pk)"
                    color="primary"
                  >
                    <v-icon class="fas fa-play-circle" x-small left></v-icon>
                    {{ $t("actions_force_run_title") }}
                  </v-btn>
                </template>
                <span>{{ $t("actions_force_run") }}</span>
              </v-tooltip>
              <v-tooltip bottom>
                <template #activator="{ on }">
                  <v-btn
                    v-if="item.isCancelPossible"
                    text
                    small
                    v-on="on"
                    @click="cancel(item)"
                    :loading="loadingActions.cancel.includes(item.pk)"
                    color="error"
                  >
                    <v-icon class="fas fa-ban" x-small left></v-icon>
                    {{ $t("actions_cancel_title") }}
                  </v-btn>
                </template>
                <span>{{ $t("actions_cancel") }}</span>
              </v-tooltip>
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
import {
  annotateIntention,
  intentionStateToIcon,
} from "@/libs/intention-state";
import CheckMark from "@/components/util/CheckMark";
import { isoDateTimeFormatSpans } from "@/libs/dates";
import AttemptExtractedData from "@/components/sushi/AttemptExtractedData";

export default {
  name: "SushiFetchIntentionsListWidget",
  components: { AttemptExtractedData, CheckMark, FetchIntentionStatusIcon },
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
      loadingActions: {
        trigger: [],
        cancel: [],
      },
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
      runnableFilterItems: [
        { value: "all", text: this.$i18n.t("runnable.all") },
        { value: "now", text: this.$i18n.t("runnable.now") },
        { value: "future", text: this.$i18n.t("runnable.future") },
        { value: "never", text: this.$i18n.t("runnable.never") },
      ],
      runnableFilter: "all",
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
    lastUpdate() {
      if (this.intentionData.length === 0) {
        return null;
      }
      return this.intentionData
        .map((item) => item.last_updated)
        .reduce((a, b) => (a > b ? a : b));
    },
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
          text: this.$t("title_fields.not_before"),
          value: "notBefore",
          tooltip: this.$t("not_before_tooltip"),
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
        .filter((item) => {
          let now = new Date();
          switch (this.runnableFilter) {
            case "never":
              return item.isFinished || item.brokenCredentials;
            case "now":
              return (
                !(item.isFinished || item.brokenCredentials) &&
                item.notBefore < now
              );
            case "future":
              return !(item.isFinished || item.brokenCredentials) >= now;
            default:
              return true;
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

    triggerUrl(pk) {
      return `${this.intentionsUrl}/${pk}/trigger/`;
    },

    cancelUrl(pk) {
      return `${this.intentionsUrl}/${pk}/cancel/`;
    },

    async forceRun(intention) {
      this.loadingActions.trigger.push(intention.pk);
      try {
        await axios.post(this.triggerUrl(intention.pk));
      } catch (error) {
        this.showSnackbar({
          content: "Error triggering intention: " + error,
          color: "error",
        });
      } finally {
        this.loadingActions.trigger = this.loadingActions.trigger.filter(
          (x) => x !== intention.pk
        );
      }
      this.fetchIntentions(false);
    },

    formatDateTime(value) {
      return isoDateTimeFormatSpans(value);
    },

    async cancel(intention) {
      this.loadingActions.cancel.push(intention.pk);
      try {
        await axios.post(this.cancelUrl(intention.pk));
      } catch (error) {
        this.showSnackbar({
          content: "Error cancelling intention: " + error,
          color: "error",
        });
      } finally {
        this.loadingActions.cancel = this.loadingActions.cancel.filter(
          (x) => x !== intention.pk
        );
      }
      this.fetchIntentions(false);
    },

    async fetchIntentions(showLoader = true) {
      if (!this.intentionsUrl) {
        return;
      }
      if (showLoader) {
        this.loading = true;
      }
      try {
        let params = {};
        if (this.intentionData.length > 0) {
          params.last_updated_after = this.lastUpdate;
        }
        let response = await axios.get(this.intentionsUrl, {
          params: params,
        });
        let newData = response.data;
        newData.forEach(annotateIntention);
        if (this.intentionData.length > 0) {
          // we already have intentions, we just want to update the changed ones
          let newpkToRecord = new Map();
          newData.forEach((record) => {
            newpkToRecord.set(record.pk, record);
          });
          for (let [i, intention] of this.intentionData.entries()) {
            if (newpkToRecord.has(intention.pk)) {
              this.intentionData.splice(i, 1, newpkToRecord.get(intention.pk));
            }
          }
        } else {
          this.intentionData = newData;
        }
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

      if (!this.inactive && this.retryTimeout) {
        // setTimeout delay (ms) can't be greater than 32bit integer
        setTimeout(
          () => this.scheduleRecheck(false),
          Math.min(1000 * 60 * 60, this.retryTimeout)
        );
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
      this.intentionData = [];
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
