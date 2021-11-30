<i18n lang="yaml" src="../locales/common.yaml"></i18n>

<i18n lang="yaml">
en:
  total_interest: Total interest
  number_of_days: Number of days with data
  interest_per_day: Average daily interest
  sushi_status: SUSHI automated harvesting status
  sushi_status_info: Result of download for each automatically harvested report.
  details_here: Details here
  interest_totals: Interest summary
  sushi_overview: SUSHI overview

cs:
  total_interest: Celkový zájem
  number_of_days: Počet dní s daty
  interest_per_day: Průměrný denní zájem
  sushi_status: Stav automatického stahování SUSHI
  sushi_status_info: Souhrn výsledku stahování pro všechny automaticky sklízené reporty.
  details_here: Podrobnosti zde
  interest_totals: Celkový zájem
  sushi_overview: Přehled SUSHI
</i18n>

<template>
  <IntroPage v-if="loggedIn && showIntro" />
  <v-container fluid v-else-if="organizationId" pa-0 pa-sm-2>
    <!--v-row>
            <v-col>
                <h1 v-text="$t('pages.dashboard')"></h1>
            </v-col>
        </v-row-->
    <v-row>
      <v-col cols="12" lg="6">
        <v-card min-height="480">
          <v-card-title
            v-text="$t('interest')"
            class="float-left pt-3"
          ></v-card-title>
          <v-card-text class="pt-3">
            <APIChart
              v-if="interestReportType"
              :organization="organizationId"
              primary-dimension="date"
              :report-type-id="interestReportType.pk"
              secondary-dimension="Interest_Type"
              raw-report-type
              stack
              dashboard-chart
            >
            </APIChart>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" lg="6">
        <v-card min-height="480">
          <v-card-title
            v-text="$t('sushi_status')"
            class="float-left"
          ></v-card-title>
          <v-card-text class="pt-3">
            <div class="text-right">
              <v-btn-toggle v-model="sushiMonth" mandatory dense>
                <v-btn
                  v-for="month in sushiMonths"
                  :key="month"
                  :value="month"
                  v-text="month"
                ></v-btn>
              </v-btn-toggle>
            </div>
            <SushiStatusChart
              :month="sushiMonth"
              :organization-id="organizationId"
            />
            <div class="font-weight-light pt-6">
              <span v-text="$t('sushi_status_info')" class="pr-1"></span>
              <span>
                <router-link
                  :to="{
                    name: 'sushi-monthly-overview',
                    query: { month: sushiMonth },
                  }"
                >
                  <span v-text="$t('details_here')"></span>
                </router-link>
              </span>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-row class="align-stretch">
      <v-col cols="auto">
        <v-card height="100%" min-height="320">
          <v-card-title v-text="$t('interest_totals')"></v-card-title>
          <v-card-text>
            <div v-if="totalInterestData" class="text-center ma-5">
              <div v-text="$t('total_interest')"></div>
              <div
                class="text-h4"
                v-text="formatInteger(totalInterestData.interest_sum)"
              ></div>
              <div class="mt-8" v-text="$t('number_of_days')"></div>
              <div
                class="text-h5"
                v-text="formatInteger(totalInterestData.days)"
              ></div>
              <div class="mt-8" v-text="$t('interest_per_day')"></div>
              <div
                class="text-h4"
                v-text="
                  smartFormatFloat(
                    totalInterestData.interest_sum / totalInterestData.days
                  )
                "
              ></div>
            </div>
            <LargeSpinner v-else />
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="auto">
        <v-card height="100%" min-height="320" min-width="200">
          <v-card-title v-text="$t('sushi_overview')"></v-card-title>
          <v-card-text>
            <SushiStatsDashboardWidget class="mx-3 mt-5" />
          </v-card-text>
        </v-card>
      </v-col>

      <v-col
        cols="auto"
        v-for="interestGroup in this.interestGroupTitlesSorted"
        :key="interestGroup.short_name"
        class="top-col"
      >
        <v-lazy min-height="320" transition="fade-transition">
          <TopTenDashboardWidget
            :request-base="titleInterestTopRequest"
            :interest-group="interestGroup"
            :pub-types="pubTypesForInterestGroup(interestGroup.short_name)"
          >
          </TopTenDashboardWidget>
        </v-lazy>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import APIChart from "@/components/APIChart";
import { mapActions, mapGetters, mapState } from "vuex";
import LargeSpinner from "@/components/util/LargeSpinner";
import { formatInteger, smartFormatFloat } from "@/libs/numbers";
import { pubTypes } from "@/libs/pub-types";
import TopTenDashboardWidget from "@/components/TopTenDashboardWidget";
import IntroPage from "./IntroPage";
import SushiStatusChart from "@/components/charts/SushiStatusChart";
import startOfMonth from "date-fns/startOfMonth";
import addDays from "date-fns/addDays";
import { ymDateFormat } from "@/libs/dates";
import SushiStatsDashboardWidget from "@/components/sushi/SushiStatsDashboardWidget";

export default {
  name: "DashboardPage",

  components: {
    SushiStatsDashboardWidget,
    SushiStatusChart,
    IntroPage,
    TopTenDashboardWidget,
    LargeSpinner,
    APIChart,
  },

  data() {
    const lastMonth = ymDateFormat(addDays(startOfMonth(new Date()), -15));
    const monthBeforeLast = ymDateFormat(
      addDays(startOfMonth(new Date()), -45)
    );
    return {
      sushiMonths: [lastMonth, monthBeforeLast],
      sushiMonth: lastMonth,
    };
  },

  computed: {
    ...mapState({ organizationId: "selectedOrganizationId" }),
    ...mapState("interest", [
      "interestGroups",
      "interestReportType",
      "totalInterestData",
    ]),
    ...mapGetters({
      dateRangeStart: "dateRangeStartText",
      dateRangeEnd: "dateRangeEndText",
      loggedIn: "loggedIn",
      showIntro: "showIntro",
    }),
    interestGroupTitlesSorted() {
      let igs = this.interestGroups.filter(
        (item) => item.short_name !== "other"
      );
      if (igs) {
        return igs.sort((a, b) =>
          a.important === b.important
            ? a.name > b.name
            : a.important < b.important
        );
      }
      return igs;
    },
    titleInterestTopRequest() {
      return this.organizationId
        ? {
            url: `/api/organization/${this.organizationId}/top-title-interest/`,
            params: { start: this.dateRangeStart, end: this.dateRangeEnd },
          }
        : null;
    },
    totalInterestRequest() {
      return this.organizationId
        ? {
            url: `/api/organization/${this.organizationId}/interest/`,
            params: { start: this.dateRangeStart, end: this.dateRangeEnd },
          }
        : null;
    },
  },

  methods: {
    ...mapActions(["loadSushiCredentialsCount"]),
    ...mapActions("interest", [
      "fetchInterestGroups",
      "fetchInterestReportType",
      "fetchTotalInterest",
    ]),
    formatInteger,
    smartFormatFloat,

    pubTypesForInterestGroup(igShortName) {
      if (igShortName.indexOf("full_text") > -1) {
        let all = { text: "pub_type.all", value: "", icon: "fa-expand" };
        return [
          all,
          ...pubTypes
            .filter((item) => "BJ".indexOf(item.code) > -1)
            .map((item) => {
              return { text: item.title, icon: item.icon, value: item.code };
            }),
        ];
      }
      return [];
    },
  },

  mounted() {
    this.loadSushiCredentialsCount();
    this.fetchInterestReportType();
    this.fetchTotalInterest(this.totalInterestRequest);
    this.fetchInterestGroups();
  },

  watch: {
    totalInterestRequest: "fetchTotalInterest",
  },
};
</script>

<style scoped lang="scss">
table.dashboard {
  width: 100%;

  th {
    text-align: left;
    padding-right: 1rem;
  }

  td {
    text-align: right;
  }
}

.top-col {
  min-width: 400px;
}
</style>
