<i18n lang="yaml">
en:
  credentials_count: Credentials
  report_count: Reports
  automatic_count: Automatically harvested credentials
  broken_count: Broken credentials
  inactive_count: Credentials with automatic harvesting disabled
  broken_report_count: Broken reports (with working credentials)
  report_from_broken_credentials_count: Reports with broken credentials
  inactive_report_count: Reports with credentials without automatic harvesting
  automatic_report_count: Automatically harvested reports

cs:
  credentials_count: Přihlašovací údaje
  report_count: Reporty
  automatic_count: Automaticky stahované přihlašovací údaje
  broken_count: Nefunkční přihlašovací údaje
  inactive_count: Přihlašovací údaje, které nejsou automaticky stahovány
  broken_report_count: Nefunkční reporty (s funkčními přihlašovacími údaji)
  report_from_broken_credentials_count: Reporty s nefunkčními přihlašovacími údaji
  inactive_report_count: Reporty s přihlašovacími údaji, které nejsou automaticky stahovány
  automatic_report_count: Automaticky stahované reporty
</i18n>

<template>
  <div class="text-center">
    <div
      v-text="$t('credentials_count')"
      style="color: rgba(0, 0, 0, 0.6)"
    ></div>
    <div class="text-h4">
      <router-link
        :to="link"
        class="text-decoration-none"
        style="color: rgba(0, 0, 0, 0.6)"
        >{{ sushiCredentialsCount }}</router-link
      >
    </div>
    <div class="text-h5 mt-1 mb-10">
      <v-tooltip location="bottom" v-if="brokenSushiCredentialsCount">
        <template #activator="{ props }">
          <span v-bind="props">
            <router-link
              class="text-error text-decoration-none mr-1"
              :to="linkBroken"
            >
              <span class="fa fa-bug small"></span
              >{{ brokenSushiCredentialsCount }}
            </router-link>
          </span>
        </template>
        {{ $t("broken_count") }}
      </v-tooltip>
      <v-tooltip location="bottom" v-if="inactiveSushiCredentialsCount">
        <template #activator="{ props }">
          <span v-bind="props" class="text-warning mr-1">
            <span class="fa fa-ban small"></span
            >{{ inactiveSushiCredentialsCount }}
          </span>
        </template>
        {{ $t("inactive_count") }}
      </v-tooltip>
      <v-tooltip location="bottom">
        <template #activator="{ props }">
          <span v-bind="props" class="text-success">
            <span class="fa fa-download small"></span
            >{{ autoDownloadedCredentials }}
          </span>
        </template>
        {{ $t("automatic_count") }}
      </v-tooltip>
    </div>
    <div v-text="$t('report_count')" style="color: rgba(0, 0, 0, 0.6)"></div>
    <div class="text-h4">
      <router-link
        :to="link"
        class="text-decoration-none"
        style="color: rgba(0, 0, 0, 0.6)"
        >{{ counterReportCount }}</router-link
      >
    </div>
    <div class="text-h5 mt-1">
      <v-tooltip location="bottom" v-if="brokenCounterReportCount">
        <template #activator="{ props }">
          <span v-bind="props">
            <router-link
              :to="linkBroken"
              class="text-orange-darken-4 text-decoration-none mr-1"
            >
              <span class="fa fa-exclamation-triangle small"></span
              >{{ brokenCounterReportCount }}
            </router-link>
          </span>
        </template>
        {{ $t("broken_report_count") }}
      </v-tooltip>
      <v-tooltip
        location="bottom"
        v-if="counterReportsFromBrokenCredentialsCount"
      >
        <template #activator="{ props }">
          <span v-bind="props">
            <router-link
              :to="linkBroken"
              class="text-error text-decoration-none mr-1"
            >
              <span class="fa fa-bug small"></span
              >{{ counterReportsFromBrokenCredentialsCount }}
            </router-link>
          </span>
        </template>
        {{ $t("report_from_broken_credentials_count") }}
      </v-tooltip>
      <v-tooltip
        location="bottom"
        v-if="counterReportsFromInactiveCredentialsCount"
      >
        <template #activator="{ props }">
          <span v-bind="props" class="text-warning mr-1">
            <span class="fa fa-ban small"></span
            >{{ counterReportsFromInactiveCredentialsCount }}
          </span>
        </template>
        {{ $t("inactive_report_count") }}
      </v-tooltip>
      <v-tooltip location="bottom">
        <template #activator="{ props }">
          <span v-bind="props" class="text-success">
            <span class="fa fa-download small"></span
            >{{ autoDownloadedReportsCount }}
          </span>
        </template>
        {{ $t("automatic_report_count") }}
      </v-tooltip>
    </div>
  </div>
</template>

<script>
import { mapState } from "vuex";
import cancellation from "@/mixins/cancellation";

export default {
  name: "SushiStatsDashboardWidget",

  mixins: [cancellation],

  data() {
    return {
      sushiCredentialsCount: 0,
      brokenSushiCredentialsCount: 0,
      inactiveSushiCredentialsCount: 0,
      counterReportCount: 0,
      brokenCounterReportCount: 0,
      counterReportsFromInactiveCredentialsCount: 0,
      counterReportsFromBrokenCredentialsCount: 0,
    };
  },

  computed: {
    ...mapState(["selectedOrganizationId"]),
    autoDownloadedCredentials() {
      return (
        this.sushiCredentialsCount -
        this.inactiveSushiCredentialsCount -
        this.brokenSushiCredentialsCount
      );
    },
    autoDownloadedReportsCount() {
      return (
        this.counterReportCount -
        this.brokenCounterReportCount -
        this.counterReportsFromBrokenCredentialsCount -
        this.counterReportsFromInactiveCredentialsCount
      );
    },
    link() {
      return { name: "sushi-credentials-list" };
    },
    linkBroken() {
      return { name: "sushi-credentials-list", query: { broken: 1 } };
    },
  },

  methods: {
    async fetchSushiCredentials() {
      if (!this.selectedOrganizationId) return;

      this.sushiCredentialsCount = 0;
      this.brokenSushiCredentialsCount = 0;
      this.inactiveSushiCredentialsCount = 0;
      this.counterReportCount = 0;
      this.brokenCounterReportCount = 0;
      this.counterReportsFromInactiveCredentialsCount = 0;
      this.counterReportsFromBrokenCredentialsCount = 0;
      const request = {
        url: "/api/sushi-credentials/",
        params: {
          organization: this.selectedOrganizationId,
          page: 1,
          page_size: 10,
        },
        label: "SUSHI credentials",
      };
      const { response } = await this.http(request);
      if (response && !response.error) {
        this.sushiCredentialsCount = response.data.count;
        this.brokenSushiCredentialsCount = response.data.broken_count;
        this.inactiveSushiCredentialsCount = response.data.inactive_count;
        this.counterReportCount = response.data.report_count;
        this.brokenCounterReportCount = response.data.broken_report_count;
        this.counterReportsFromBrokenCredentialsCount =
          response.data.report_from_broken_credentials_count;
        this.counterReportsFromInactiveCredentialsCount =
          response.data.report_from_inactive_credentials_count;
      }
    },
  },

  mounted() {
    this.fetchSushiCredentials();
  },

  watch: {
    selectedOrganizationId: "fetchSushiCredentials",
  },
};
</script>

<style scoped lang="scss">
@use "sass:math";
span.small {
  font-size: math.div(9, 16) * 100%;
  padding-right: 4px;
  vertical-align: middle;
}

.default--text {
  color: rgba(0, 0, 0, 0.6);
}
</style>
