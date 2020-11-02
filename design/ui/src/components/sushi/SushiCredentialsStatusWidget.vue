<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml">
en:
  in_progress: Fetching data
  waiting: Waiting for download slot
  fetching_details: Fetching details
  no_data_yet: There are no data yet, please wait until the download finishes. It can take from seconds to minutes.

cs:
  in_progress: Stahuji data
  waiting: Čekám, až bude možné stahovat data
  fetching_details: Stahuji informace
  no_data_yet: Data ještě nejsou k dispozici - vyčkejte prosím, až budou stáhnutá. Může to trvat od sekund po jednotky minut.
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
      <v-row v-else-if="!intentionData.attempt">
        <v-col cols="auto">
          <span v-if="showPlatform">{{ intentionData.platform_name }} &gt; </span>
          <strong v-text="intentionData.counter_report_code"></strong>
          <div
            v-if="showOrganization"
            class="font-weight-light font-italic"
            v-text="intentionData.organization_name"
          ></div>
        </v-col>
        <v-col>
          <v-progress-linear height="1.5rem" indeterminate>
            <span v-if="intentionData.fetching_data">
            {{ $t("in_progress") }}, {{ elapsedTime }} s
            </span>
            <span v-else>
            {{ $t("waiting") }}, {{ elapsedTime }} s
            </span>
          </v-progress-linear>
        </v-col>
      </v-row>
      <v-row v-else-if="intentionData.attempt">
        <v-col cols="auto">
          <span v-if="showPlatform">{{ intentionData.platform_name }} &gt; </span>
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
      <span
        v-if="!intentionData || intentionData.fetching_data"
        v-text="$t('no_data_yet')"
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
import { mapActions } from "vuex";
import axios from "axios";
import GoodBadMark from "@/components/util/GoodBadMark";

export default {
  name: "SushiCredentialsStatusWidget",
  components: { GoodBadMark },
  props: {
    intentionId: {
      required: true,
      type: Number,
    },
    harvestId: {
      required: true,
      type: Number,
    },
    retryInterval: { default: 1000, type: Number },
    showOrganization: { default: false, type: Boolean },
    showPlatform: { default: false, type: Boolean },
  },
  data() {
    return {
      intentionData: null,
      startTime: null,
      now: null,
      lastCheck: null,
      inactive: false,
    };
  },
  computed: {
    elapsedTime() {
      return Math.round((this.now - this.startTime) / 1000);
    },
  },
  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    async check() {
      try {
        let response = await axios.get(
          `/api/scheduler/harvest/${this.harvestId}/intention/${this.intentionId}/`
        );
        this.intentionData = response.data;
        if ((!this.intentionData || !this.intentionData.attempt || this.intentionData.fetching_data) && !this.inactive) {
          setTimeout(this.check, this.retryInterval);
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
  mounted() {
    this.startTime = new Date().getTime();
    this.check();
    setInterval(() => {
      this.now = new Date().getTime();
    }, 200);
  },
  beforeDestroy() {
    this.inactive = true;
  },
};
</script>

<style scoped></style>
