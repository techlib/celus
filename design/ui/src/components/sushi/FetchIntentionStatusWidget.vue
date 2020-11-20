<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml">
en:
  in_progress: Fetching data
  waiting: Waiting until download is possible
  fetching_details: Fetching details
  currently_downloading: There are no data yet, please wait until the download finishes. It can take from seconds to minutes.
  planned_to_download: Fetching of data was planned, but attempt hasn't been executed yet.
  planned_for_retry: "Based on result of previous attempt, later retry was planned. The new attempt is planned for {date}. "
  deleted: Deleted
  attempt_deleted: Download was executed but information about the download were deleted.
  planned_for_later: Planned for later
  retry_planned_for_later: Retry planned for later
  start: start in
  future_start_info: Harvesting is currently waiting for free slot in the download queue.
  is_duplicate: This harvesting attempt duplicates an already planned one, so it was removed from harvesting. Click to see info on the related attempt.
  broken_credentials: The SUSHI credentials were marked as broken. Download is postponed until the credentials are fixed.
  broken_credentials_hint: You can fix the credentials on the {link} page. This link automatically applies filter limiting displayed credentials to only the broken ones.

cs:
  in_progress: Stahuji data
  waiting: Čekám, až bude možné stahovat data
  fetching_details: Stahuji informace
  currently_downloading: Data ještě nejsou k dispozici - vyčkejte prosím, až budou stáhnutá. Může to trvat od sekund po jednotky minut.
  planned_to_download: Stahování dat bylo naplánováno, ale zatím nebylo provedeno.
  planned_for_retry: "Na základě předchozího pokusu bylo naplánováno pozdější stažení. Nový pokus je naplánovaný na {date}. "
  deleted: Smazáno
  attempt_deleted: Stahování proběhlo, ale informace o stahování byly smazány.
  planned_for_later: Naplánováno na později
  retry_planned_for_later: Opakování naplánováno na později
  start: začátek za
  future_start_info: Stahování aktuálně čeká na uvolnění místa ve frontě.
  is_duplicate: Tento pokus o stažení duplikuje již naplánované stahování a byl tedy odstraněn z plánu. Klikněte pro informace o přidruženém stahování.
  broken_credentials: Přihlašovací údaje pro SUSHI byly označeny jako nefunkční. Stahování bylo pozastaveno dokud nebudou přihlašovací údaje opraveny.
  broken_credentials_hint: Přihlašovací údaje můžete opravit na stránce {link}. Tento odkaz automaticky zapne filtr, který zobrazí jen problematické přihlašovací údaje.
</i18n>
<template>
  <v-expansion-panel>
    <v-expansion-panel-header v-slot="{ open }">
      <v-progress-linear
        v-if="intentionData === null"
        height="1.5rem"
        indeterminate
      >
        <span v-text="$t('fetching_details')"></span>
      </v-progress-linear>

      <v-row
        v-else-if="!intentionData.attempt && !intentionData.when_processed"
      >
        <v-col cols="auto">
          <span v-if="showPlatform"
            >{{ intentionData.platform_name }} &gt;
          </span>
          <strong v-text="intentionData.counter_report_code"></strong>
          <div
            v-if="showOrganization"
            class="font-weight-light font-italic"
            v-text="intentionData.organization_name"
          ></div>
        </v-col>
        <v-col>
          <span v-if="futureStart">
            {{
              isRetry ? $t("retry_planned_for_later") : $t("planned_for_later")
            }}, {{ $t("start") }}: {{ tilStart }}
            <v-icon small class="ml-3" color="#999999"
              >fa fa-hourglass-half</v-icon
            >
          </span>
          <v-progress-linear
            height="1.5rem"
            indeterminate
            v-else-if="intentionData.fetching_data"
          >
            {{ $t("in_progress") }}, {{ elapsedTime }}
          </v-progress-linear>
          <span v-else-if="isDuplicate">
            <v-icon small color="warning">fa fa-ban</v-icon>
            {{ $t("is_duplicate") }}
          </span>
          <span v-else-if="intentionData.broken_credentials">
            <v-icon small color="error">fa fa-bug</v-icon>
            {{ $t("broken_credentials") }}
          </span>
          <span v-else>
            <v-progress-circular
              indeterminate
              size="20"
              color="#999999"
              class="mr-2"
            />
            {{ $t("waiting") }}, {{ elapsedTime }}
          </span>
        </v-col>
      </v-row>

      <v-row v-else-if="!intentionData.attempt && intentionData.when_processed">
        <v-col cols="auto">
          <span v-if="showPlatform"
            >{{ intentionData.platform_name }} &gt;
          </span>
          <strong v-text="intentionData.counter_report_code"></strong>
          <div
            v-if="showOrganization"
            class="font-weight-light font-italic"
            v-text="intentionData.organization_name"
          ></div>
        </v-col>
        <v-col>
          <v-icon small>fa-exclamation-circle</v-icon>
          {{ $t("deleted") }}
        </v-col>
      </v-row>

      <v-row v-else-if="intentionData.attempt">
        <v-col cols="auto">
          <span v-if="showPlatform"
            >{{ intentionData.platform_name }} &gt;
          </span>
          <strong v-text="intentionData.counter_report_code"></strong>
          <div
            v-if="showOrganization"
            class="font-weight-light font-italic"
            v-text="intentionData.organization_name"
          ></div>
        </v-col>
        <v-col>
          {{ $t("title_fields.download_success") }}:
          <GoodBadMark
            :value="intentionData.attempt.download_success"
            extra-classes="fa-fw"
          ></GoodBadMark>
          {{ $t("title_fields.processing_success") }}:
          <GoodBadMark
            :value="intentionData.attempt.processing_success"
            extra-classes="fa-fw"
          ></GoodBadMark>
          {{ $t("title_fields.contains_data") }}:
          <GoodBadMark
            :value="intentionData.attempt.contains_data"
            extra-classes="fa-fw"
          ></GoodBadMark>
        </v-col>
      </v-row>
    </v-expansion-panel-header>

    <v-expansion-panel-content>
      <span v-if="intentionData === null"></span>
      <span
        v-else-if="
          !intentionData.when_processed &&
          !intentionData.fetching_data &&
          !isDuplicate &&
          !intentionData.broken_credentials
        "
      >
        <i18n
          :path="isRetry ? 'planned_for_retry' : 'planned_to_download'"
          tag="span"
        >
          <template #date>{{ notBeforeHuman }}</template>
        </i18n>
        <span v-if="!futureStart" v-text="$t('future_start_info')"></span>
      </span>
      <span v-else-if="isDuplicate">
        <v-expansion-panels>
          <FetchIntentionStatusWidget
            :intention-id="intentionData.duplicate_of.pk"
            :show-organization="showOrganization"
            :show-platform="showPlatform"
          />
        </v-expansion-panels>
      </span>
      <span
        v-else-if="
          intentionData.broken_credentials && !intentionData.when_processed
        "
      >
        <i18n path="broken_credentials_hint">
          <template #link>
            <router-link
              :to="{ name: 'sushi-credentials-list', query: { broken: 1 } }"
              >{{ $t("pages.sushi_management") }}</router-link
            >
          </template>
        </i18n>
      </span>
      <span
        v-else-if="!intentionData.when_processed"
        v-text="$t('currently_downloading')"
      ></span>
      <span
        v-else-if="intentionData.when_processed && !intentionData.attempt"
        v-text="$t('attempt_deleted')"
      ></span>
      <div v-else>
        <div v-if="intentionData.attempt && intentionData.attempt.data_file">
          <strong>{{ $t("title_fields.data_file") }}</strong
          >:
          <a :href="intentionData.attempt.data_file" target="_blank">{{
            intentionData.attempt.data_file
          }}</a>
        </div>
        <div v-if="intentionData.attempt && intentionData.attempt.error_code">
          <strong>{{ $t("title_fields.error_code") }}</strong
          >: {{ intentionData.attempt.error_code }}
        </div>
        <div v-if="intentionData.attempt && intentionData.attempt.log">
          <strong>{{ $t("title_fields.log") }}</strong
          >: {{ intentionData.attempt.log }}
        </div>
      </div>
    </v-expansion-panel-content>
  </v-expansion-panel>
</template>

<script>
import { mapActions, mapGetters, mapState } from "vuex";
import axios from "axios";
import GoodBadMark from "@/components/util/GoodBadMark";
import { parseDateTime } from "@/libs/dates";
import formatDistanceToNowStrict from "date-fns/formatDistanceToNowStrict";
import isFuture from "date-fns/isFuture";
import differenceInMilliseconds from "date-fns/differenceInMilliseconds";
import formatRelative from "date-fns/formatRelative";
import intervalToDuration from "date-fns/intervalToDuration";
import formatDuration from "date-fns/formatDuration";

export default {
  name: "FetchIntentionStatusWidget",
  components: { GoodBadMark },
  props: {
    initialIntentionData: {
      required: false,
      type: Object,
      default: null,
    },
    intentionId: {
      required: true,
      type: Number,
    },
    harvestId: {
      required: false,
      type: Number,
      default: null,
    },
    retryInterval: { default: 1000, type: Number },
    showOrganization: { default: false, type: Boolean },
    showPlatform: { default: false, type: Boolean },
  },

  data() {
    return {
      intentionData: this.initialIntentionData,
      startTime: null,
      now: null,
      lastCheck: null,
      inactive: false,
    };
  },

  computed: {
    ...mapState({
      currentLocale: "appLanguage",
    }),
    ...mapGetters({
      dateFnOptions: "dateFnOptions",
    }),
    elapsedTime() {
      const duration = intervalToDuration({
        start: this.notBefore,
        end: this.now,
      });
      return formatDuration(duration, this.dateFnOptions);
    },
    notBefore() {
      return parseDateTime(this.intentionData.not_before);
    },
    tilStart() {
      return formatDistanceToNowStrict(this.notBefore, this.dateFnOptions);
    },
    futureStart() {
      return isFuture(this.notBefore) && !this.isDuplicate;
    },
    isRetry() {
      if (!this.intentionData) {
        return false;
      }
      return (
        this.intentionData.data_not_ready_retry ||
        this.intentionData.service_not_available_retry ||
        this.intentionData.service_busy_retry
      );
    },
    isDuplicate() {
      if (!this.intentionData) {
        return false;
      }
      return !!this.intentionData.duplicate_of;
    },
    notBeforeHuman() {
      if (this.notBefore) {
        return formatRelative(this.notBefore, this.now, this.dateFnOptions);
      }
      return "-";
    },
    checkUrl() {
      if (this.harvestId) {
        return `/api/scheduler/harvest/${this.harvestId}/intention/${this.intentionId}/`;
      }
      return `/api/scheduler/intention/${this.intentionId}/`;
    },
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    async check() {
      try {
        let response = await axios.get(this.checkUrl);
        this.intentionData = response.data;
        if (
          (!this.intentionData || !this.intentionData.when_processed) &&
          !this.isDuplicate &&
          !this.inactive &&
          !this.intentionData.broken_credentials
        ) {
          // plan refresh - for stuff planned in future refresh at notBefore, for stuff planned in past use retryInterval
          const naturalTimout = differenceInMilliseconds(
            this.notBefore,
            this.now
          );
          setTimeout(
            this.check,
            naturalTimout > 0 ? naturalTimout : this.retryInterval
          );
        }
      } catch (error) {
        this.showSnackbar({
          content: "Error checking SUSHI attemps: " + error,
          color: "error",
        });
      }
    },
    stop() {
      this.inactive = true;
    },
  },

  created() {
    this.startTime = new Date();
    this.now = new Date();
  },

  mounted() {
    if (!this.intentionData || !this.intentionData.attempt) {
      this.check();
    }
    setInterval(() => {
      this.now = new Date();
    }, 250);
  },
  beforeDestroy() {
    this.inactive = true;
  },
};
</script>

<style scoped></style>
