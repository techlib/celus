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
    <div v-text="$t('credentials_count')"></div>
    <div class="text-h4">
      <router-link :to="link" class="text-decoration-none default--text">{{
        credentialsCount
      }}</router-link>
    </div>

    <div class="text-h5 mt-1 mb-10">
      <v-tooltip bottom v-if="brokenCredentialsCount">
        <template #activator="{ on }">
          <span v-on="on">
            <router-link
              class="error--text text-decoration-none"
              :to="linkBroken"
            >
              <span class="fa fa-bug small"></span>{{ brokenCredentialsCount }}
            </router-link>
          </span>
        </template>
        {{ $t("broken_count") }}
      </v-tooltip>

      <v-tooltip bottom v-if="inactiveCredentialsCount">
        <template #activator="{ on }">
          <span v-on="on" class="warning--text">
            <span class="fa fa-ban small"></span>{{ inactiveCredentialsCount }}
          </span>
        </template>
        {{ $t("inactive_count") }}
      </v-tooltip>

      <v-tooltip bottom>
        <template #activator="{ on }">
          <span v-on="on" class="success--text">
            <span class="fa fa-download small"></span
            >{{ autoDownloadedCredentials }}
          </span>
        </template>
        {{ $t("automatic_count") }}
      </v-tooltip>
    </div>

    <div v-text="$t('report_count')"></div>
    <div class="text-h4">
      <router-link :to="link" class="default--text text-decoration-none">{{
        reportCount
      }}</router-link>
    </div>

    <div class="text-h5 mt-1">
      <v-tooltip bottom v-if="brokenReportsCount">
        <template #activator="{ on }">
          <span v-on="on">
            <router-link
              :to="linkBroken"
              class="orange--text text--darken-4 text-decoration-none"
            >
              <span class="fa fa-exclamation-triangle small"></span
              >{{ brokenReportsCount }}
            </router-link>
          </span>
        </template>
        {{ $t("broken_report_count") }}
      </v-tooltip>

      <v-tooltip bottom v-if="reportsFromBrokenCredentialsCount">
        <template #activator="{ on }">
          <span v-on="on">
            <router-link
              :to="linkBroken"
              class="error--text text-decoration-none"
            >
              <span class="fa fa-bug small"></span
              >{{ reportsFromBrokenCredentialsCount }}
            </router-link>
          </span>
        </template>
        {{ $t("report_from_broken_credentials_count") }}
      </v-tooltip>

      <v-tooltip bottom v-if="inactiveReportsCount">
        <template #activator="{ on }">
          <span v-on="on" class="warning--text">
            <span class="fa fa-ban small"></span>{{ inactiveReportsCount }}
          </span>
        </template>
        {{ $t("inactive_report_count") }}
      </v-tooltip>

      <v-tooltip bottom>
        <template #activator="{ on }">
          <span v-on="on" class="success--text">
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
import { mapActions, mapState } from "vuex";
import axios from "axios";

export default {
  name: "SushiStatsDashboardWidget",

  data() {
    return {
      sushiCredentials: [],
    };
  },

  computed: {
    ...mapState({
      selectedOrganizationId: "selectedOrganizationId",
    }),
    sushiCredentialsUrl() {
      if (this.selectedOrganizationId) {
        return `/api/sushi-credentials/?organization=${this.selectedOrganizationId}`;
      }
      return null;
    },
    credentialsCount() {
      return this.sushiCredentials.length;
    },
    brokenCredentialsCount() {
      return this.sushiCredentials.filter((item) => !!item.broken).length;
    },
    inactiveCredentialsCount() {
      return this.sushiCredentials.filter((item) => !item.enabled).length;
    },
    autoDownloadedCredentials() {
      return (
        this.credentialsCount -
        this.inactiveCredentialsCount -
        this.brokenCredentialsCount
      );
    },
    reportCount() {
      let count = 0;
      this.sushiCredentials.forEach(
        (item) => (count += item.counter_reports_long.length)
      );
      return count;
    },
    reportsFromBrokenCredentialsCount() {
      let count = 0;
      this.sushiCredentials
        .filter((item) => !!item.broken)
        .forEach((item) => (count += item.counter_reports_long.length));
      return count;
    },
    brokenReportsCount() {
      let count = 0;
      this.sushiCredentials.forEach(
        (item) =>
          (count += item.counter_reports_long.filter(
            (report) => !!report.broken
          ).length)
      );
      return count;
    },
    inactiveReportsCount() {
      let count = 0;
      this.sushiCredentials
        .filter((item) => !item.enabled)
        .forEach((item) => (count += item.counter_reports_long.length));
      return count;
    },
    autoDownloadedReportsCount() {
      return (
        this.reportCount -
        this.brokenReportsCount -
        this.reportsFromBrokenCredentialsCount -
        this.inactiveReportsCount
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
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    async fetchSushiCredentials() {
      if (this.sushiCredentialsUrl) {
        this.sushiCredentials = [];
        try {
          let result = await axios.get(this.sushiCredentialsUrl);
          this.sushiCredentials = result.data;
        } catch (error) {
          this.showSnackbar({
            content: "Could not load SUSHI credentials: " + error,
            color: "error",
          });
        }
      }
    },
  },

  mounted() {
    this.fetchSushiCredentials();
  },

  watch: {
    sushiCredentialsUrl() {
      this.fetchSushiCredentials();
    },
  },
};
</script>

<style scoped lang="scss">
span.small {
  font-size: (9/16) * 100%;
  padding-right: 4px;
  vertical-align: middle;
}

.default--text {
  color: rgba(0, 0, 0, 0.6);
}
</style>
