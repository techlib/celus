<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml">
en:
  click_to_see_details: Click on cards of individual reports to see more details.
  date_change_hint: (use the date range selector on top of the page to change it)
  detail_by_platform_and_month: Data coverage by platform and month
  harvest_missing: Harvest missing {count} month | Harvest missing {count} months
  months_present: "{count} month present | {count} months present"
  months_harvestable: "{count} month with SUSHI but old | {count} months with SUSHI but old"
  months_no_sushi: "{count} month without working SUSHI | {count} months without working SUSHI"
  months_auto_harvestable: "{count} month harvestable and recent enough | {count} months harvestable and recent enough"
  all_harvested: Perfect, no data is missing
  nothing_to_harvest: Unfortunately no missing data can be obtained automatically via SUSHI
  detail_by_organization: Detail by organization
  click_chart_for_organizations: Click on specific chart cell to get detail by organization
  harvest_missing_data: Harvest missing data
  credentials_count: "{count} set of credential | {count} sets of credentials"
  month_count: "{count} month | {count} months"
  platforms_count: "{count} platform | {count} platforms"
  selected: Selected
  harvest_selected: Harvest selected
  no_data: |
    Unfortunately there are no data yet for calculation of data coverage. Either upload some data manually
    or harvest it via SUSHI.
  implicit_end_date: |
    When the end date is the current date, we use the month before the last finished month as the end date
    (for example in May we use March). This is because data for the previous month may not be completely
    available over SUSHI yet.
  intro: |
    This page shows data coverage for all reports and all active platforms in the selected time period.
    Data coverage is calculated
    as the number of months for which data is available divided by the number of months for which data
    is expected. By clicking on cards of individual reports you can identify for which platforms
    and which months data is missing. In case functional SUSHI is present, it is possible to harvest
    missing data automatically directly from this page.
  date_limit_info: |
    In order to limit traffic to SUSHI servers and avoid long waiting times, automatic harvesting
    of missing data will only be performed for months within the COUNTER Code of Practice 5 data
    retention period (this year + previous two whole years). For older months you can still harvest
    data manually via the SUSHI management page.

cs:
  click_to_see_details: Klikněte na karty jednotlivých reportů pro více detailů.
  date_change_hint: (použijte výběr data na horním okraji stránky pro změnu)
  detail_by_platform_and_month: Detail pokrytí podle platformy a měsíce
  harvest_missing: Získat chybějící {count} měsíc | Získat chybějící {count} měsíce | Získat chybějících {count} měsíců
  months_present: "{count} měsíc stažen | {count} měsíce staženy | {count} měsíců staženo"
  months_harvestable: "{count} měsíc stažitelný | {count} měsíce stažitelné | {count} měsíců stažitelných"
  months_no_sushi: "{count} měsíc bez funkčního SUSHI | {count} měsíce bez funkčního SUSHI | {count} měsíců bez funkčního SUSHI"
  months_auto_harvestable: "{count} měsíc stažitelný a dostatečně aktuální | {count} měsíce stažitelné a dostatečně aktuální | {count} měsíců stažitelných a dostatečně aktuálních"
  all_harvested: Skvěle, nechybí žádná data
  nothing_to_harvest: Bohužel žádná chybějící data nelze získat automaticky pomocí SUSHI
  detail_by_organization: Detail podle organizace
  click_chart_for_organizations: Klikněte na konkrétní buňku grafu pro detail podle organizace
  harvest_missing_data: Získat chybějící data
  credentials_count: "{count} sada přihlašovacích údajů | {count} sady přihlašovacích údajů | {count} sad přihlašovacích údajů"
  month_count: "{count} měsíc | {count} měsíce | {count} měsíců"
  platforms_count: "{count} platforma | {count} platformy | {count} platforem"
  selected: Vybráno
  harvest_selected: Získat vybrané
  no_data: |
    Bohužel zatím nejsou k dispozici žádná data pro vypočet pokrytí. Buď nahrajte
    nějaká data ručně, nebo je stáhněte pomocí SUSHI.
  implicit_end_date: |
    Pokud je konečné datum nastavené na aktuální datum, používáme zde předposlední dokončený měsíc
    (např. v květnu je to březen). Je to proto, že data pro poslední dokončený měsíc nemusí být přes SUSHI ještě úplně k
    dispozici.
  intro: |
    Tato stránka zobrazuje pokrytí dat pro všechny reporty a aktivní platformy ve zvoleném časovém období.
    Pokrytí dat je vypočítáno
    jako počet měsíců, pro které jsou data k dispozici, děleno počtem měsíců, pro které jsou data očekávána.
    Kliknutím na karty jednotlivých reportů můžete zjistit, pro které platformy a které měsíce chybí data.
    V případě funkčního SUSHI je možné chybějící data stáhnout přímo z této stránky.
  date_limit_info: |
    Abychom omezili provoz na SUSHI serverech a zabránili dlouhým čekacím dobám, automatické stahování
    chybějících dat bude prováděno pouze pro měsíce v rámci období uchovávání dat podle COUNTER Code of Practice 5
    (tento rok + předchozí dva celé roky). Pro starší měsíce můžete stále data stáhnout
    ručně pomocí stránky pro správu SUSHI.
</i18n>

<template>
  <v-container fluid>
    <v-row>
      <v-col>
        <h2>{{ $t("pages.data_coverage_overview") }}</h2>
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        {{ $t("intro") }}
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <span class="font-weight-bold text--secondary">{{
          $t("labels.date_range")
        }}</span
        >: {{ dateRangeStart }} -
        {{ dateRangeCoverageEndText }}
        <v-tooltip bottom max-width="600px">
          <template #activator="{ on }">
            <v-icon color="info" v-on="on">fa fa-info-circle</v-icon>
          </template>
          <span>{{ $t("implicit_end_date") }}</span>
        </v-tooltip>
        <span class="text-caption text--disabled ms-3">{{
          $t("date_change_hint")
        }}</span>
      </v-col>
    </v-row>
    <v-row>
      <v-expansion-panels
        accordion
        v-model="openedPanel"
        flat
        class="bordered-panel"
      >
        <v-expansion-panel v-for="cv in counterVersions" :value="cv" :key="cv">
          <v-expansion-panel-header class="justify-space-between">
            <div class="flex-grow-0 me-4">
              {{
                cv
                  ? "COUNTER " + counterVersionToStr(cv)
                  : $t("title_fields.non_counter")
              }}
            </div>
            <v-spacer />
            <div class="mx-4" style="max-width: 200px">
              <v-progress-linear
                v-if="progressByCounterVersion(cv) < 1"
                :value="100 * progressByCounterVersion(cv)"
                color="grey lighten-2"
                height="20"
                class="text-caption"
              >
                {{ $t("labels.loading") }}
              </v-progress-linear>
              <v-progress-linear
                v-else
                :value="roundValue(ratioByCounterVersion(cv))"
                :color="colorSuccess(ratioByCounterVersion(cv), true)"
                height="20"
                class="text-caption"
              >
                <span class="hidden-sm-and-down">
                  {{ $t("labels.total_coverage") }}:
                </span>
                {{ roundValue(ratioByCounterVersion(cv)) }}
                %
              </v-progress-linear>
            </div>
          </v-expansion-panel-header>

          <v-expansion-panel-content>
            <v-row class="my-3">
              <v-col
                v-for="reportType in visibleReportTypes.filter(
                  (rt) => rt.counter_version === cv
                )"
                :key="reportType.pk"
                cols="6"
                md="3"
                lg="2"
                xl="1"
              >
                <CoverageCard
                  :report-type="reportType"
                  :coverage-data="coverageData[reportType.pk]"
                  :selected="selectedReportTypeId === reportType.pk"
                  :refreshing="
                    refreshingSelected && selectedReportTypeId === reportType.pk
                  "
                  show-platform-count
                  :show-organization-count="showingAllOrganizations"
                  @click="rtClick({ reportType: reportType })"
                />
              </v-col>
            </v-row>
          </v-expansion-panel-content>
        </v-expansion-panel>
      </v-expansion-panels>
    </v-row>
    <v-row class="pt-6" id="detailTop">
      <v-col v-if="selectedReportType">
        <h3>{{ selectedReportType.name }}</h3>
      </v-col>
    </v-row>
    <v-row v-if="selectedReportType" v-intersect="onDetailIntersect">
      <v-col
        align-self="center"
        cols="12"
        :md="userCanHarvest ? 6 : 12"
        :lg="userCanHarvest ? 8 : 12"
        :xl="userCanHarvest ? 9 : 12"
      >
        <CompositionBar
          :data="compositionBarData"
          height="36"
          show-all-tooltips-as-one
          ref="compositionBar"
        />
      </v-col>
      <v-col v-if="userCanHarvest" cols="12" md="6" lg="4" xl="3">
        <v-btn
          v-if="harvestInfo && selectedWillingToHarvestCount"
          color="primary"
          class="ms-2"
          @click="showHarvestDialog = true"
        >
          {{ $tc("harvest_missing", selectedWillingToHarvestCount) }}
        </v-btn>
        <span v-else-if="harvestInfo && selectedMissingCount">{{
          $t("nothing_to_harvest")
        }}</span>
        <span v-else-if="!selectedMissingCount">
          <v-icon color="success">fa fa-thumbs-up</v-icon>
          {{ $t("all_harvested") }}
        </span>
      </v-col>
    </v-row>
    <v-row v-if="selectedHarvestableCount > selectedWillingToHarvestCount">
      <v-col>
        <v-alert type="info" text>{{ $t("date_limit_info") }}</v-alert>
      </v-col>
    </v-row>

    <v-row v-if="selectedReportType" class="pt-6">
      <v-col cols="auto" class="align-self-center">
        <h4 class="font-weight-ight">
          {{ $t("detail_by_platform_and_month") }}
        </h4>
      </v-col>
      <v-col
        v-if="showingAllOrganizations"
        class="text-caption font-weight-ight align-self-center"
      >
        (<v-icon small>far fa-hand-pointer</v-icon>
        {{ $t("click_chart_for_organizations") }})
      </v-col>
    </v-row>
    <v-row v-else-if="!loading" class="pt-6">
      <v-col>
        <v-alert type="info" text class="mb-0">
          {{
            reportTypes.length === 0
              ? $t("no_data")
              : $t("click_to_see_details")
          }}
        </v-alert>
      </v-col>
    </v-row>

    <v-row v-if="selectedReportType">
      <v-col class="pa-0">
        <CoverageMap
          :report-type-id="selectedReportType.pk"
          :start-month="dateRangeStart"
          :end-month="dateRangeCoverageEndText"
          :organization-id="organizationId > 0 ? organizationId : undefined"
          rows="platform"
          cols="date"
          raw-report-type
          sort-by-coverage
          @click="onClick"
          ref="rtCoverageMap"
        />
      </v-col>
    </v-row>
    <v-dialog
      v-model="showDetailByOrganization"
      v-if="showDetailByOrganization"
    >
      <v-card>
        <v-card-title class="text-h5">
          {{ $t("detail_by_organization") }}
        </v-card-title>
        <v-card-subtitle class="pt-2">
          {{ $t("labels.platform") }}:
          {{ selectedPoint.platform }}
        </v-card-subtitle>
        <v-card-text>
          <CoverageMap
            :report-type-id="selectedReportType.pk"
            :start-month="dateRangeStart"
            :end-month="dateRangeCoverageEndText"
            :platform-id="selectedPoint.platformId"
            :organization-id="organizationId > 0 ? organizationId : undefined"
            rows="organization"
            cols="date"
            raw-report-type
            sort-by-coverage
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="showDetailByOrganization = false" class="mb-3 me-3">
            {{ $t("actions.close") }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog
      v-model="showHarvestDialog"
      v-if="showHarvestDialog"
      :max-width="harvestId ? '1200px' : '800px'"
    >
      <v-card v-if="harvestId">
        <v-card-title>{{ $t("harvest_missing_data") }}</v-card-title>
        <v-card-text>
          <SushiFetchIntentionsListWidget
            :harvest-id="harvestId"
            ref="intentionsList"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="showHarvestDialog = false" class="mb-3 me-3">
            {{ $t("actions.close") }}
          </v-btn>
        </v-card-actions>
      </v-card>

      <v-card v-else>
        <v-card-title>{{ $t("harvest_missing_data") }}</v-card-title>
        <v-card-text>
          <v-data-table
            :items="selectedHarvestablePlatforms"
            :headers="harvestablePlatformsHeaders"
            show-select
            item-key="platform"
            v-model="platformsToHarvest"
            dense
          >
            <template #item.records="{ item }">
              {{ item.records.length }}
            </template>
            <template #top>
              <div class="d-flex align-center pb-3">
                <span>
                  <span class="font-weight-bold">{{ $t("selected") }}:</span>
                  <span>
                    {{ $tc("platforms_count", platformsToHarvest.length) }} /
                    {{ $tc("credentials_count", selectedCredentialsCount) }} /
                    {{ $tc("month_count", selectedMonthCount) }}
                  </span>
                </span>
                <v-spacer></v-spacer>
                <v-btn @click="selectAllPlatforms" small class="mx-2">
                  {{ $t("actions.select_all") }}
                </v-btn>
                <v-btn @click="unselectAllPlatforms" small class="mx-2">
                  {{ $t("actions.clear_selection") }}
                </v-btn>
              </div>
            </template>
          </v-data-table>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            color="primary"
            @click="harvestSelected()"
            :disabled="selectedMonthCount === 0"
            class="mb-3 me-3"
          >
            {{ $t("harvest_selected") }}
          </v-btn>
          <v-btn @click="showHarvestDialog = false" class="mb-3 me-3">
            {{ $t("actions.close") }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    <div
      style="
        z-index: 50;
        text-align: center;
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
      "
      v-if="!isDetailVisible && selectedReportType"
    >
      <span @click="$vuetify.goTo('#detailTop')" id="scrollBtn">
        <v-icon color="white">fa-angle-down</v-icon>
      </span>
    </div>
  </v-container>
</template>

<script>
import cancellation from "@/mixins/cancellation";
import { mapGetters, mapState } from "vuex";
import CoverageMap from "@/components/charts/CoverageMap.vue";
import CompositionBar from "@/components/util/CompositionBar.vue";
import {
  counterGuaranteedPeriodStartDate,
  monthLastDay,
  ymDateFormat,
} from "@/libs/dates";
import parseISO from "date-fns/parseISO";
import SushiFetchIntentionsListWidget from "@/components/sushi/SushiFetchIntentionsListWidget.vue";
import CoverageCard from "@/components/coverage/CoverageCard.vue";
import stateTracking from "@/mixins/stateTracking";
import { counterVersionToStr } from "@/libs/sushi";

export default {
  name: "DataCoverageOverviewPage",

  mixins: [cancellation, stateTracking],

  components: {
    CoverageCard,
    SushiFetchIntentionsListWidget,
    CompositionBar,
    CoverageMap,
  },

  data() {
    return {
      reportTypes: [],
      coverageData: {},
      loading: false,
      selectedReportTypeId: null,
      openedPanel: null,
      harvestInfo: null,
      showDetailByOrganization: false,
      selectedPoint: {},
      showHarvestDialog: false,
      platformsToHarvest: [],
      harvestId: null,
      refreshingSelected: false,
      isDetailVisible: false,
      // state tracking support
      watchedAttrs: [
        {
          name: "selectedReportTypeId",
          type: Number,
          var: "rtid",
        },
        {
          name: "openedPanel",
          type: Number,
        },
      ],
    };
  },

  computed: {
    ...mapState({
      organizationId: "selectedOrganizationId",
      dateRangeEnd: "dateRangeEnd",
    }),
    ...mapGetters({
      dateRangeStart: "dateRangeStartText",
      dateRangeCoverageEndText: "dateRangeCoverageEndText",
      showAdminStuff: "showAdminStuff",
    }),
    showingAllOrganizations() {
      return this.organizationId <= 0;
    },
    selectedReportType() {
      return (
        this.reportTypes.find((rt) => rt.pk === this.selectedReportTypeId) ||
        null
      );
    },
    visibleReportTypes() {
      return this.reportTypes
        .filter((reportType) => reportType.short_name !== "interest")
        .sort((a, b) =>
          a.counter_version === b.counter_version
            ? a.name.localeCompare(b.name)
            : b.counter_version - a.counter_version
        );
    },
    counterVersions() {
      return [
        ...new Set(this.visibleReportTypes.map((rt) => rt.counter_version)),
      ].sort((a, b) => (a === null ? 1 : (b === null ? -1 : b - a))); // prettier-ignore
    },
    selectedIbCount() {
      if (!this.selectedReportType) {
        return 0;
      }
      return this.coverageData[this.selectedReportType.pk]?.ib_count;
    },
    selectedIbMax() {
      if (!this.selectedReportType) {
        return 0;
      }
      return this.coverageData[this.selectedReportType.pk]?.ib_max;
    },
    selectedMissingCount() {
      return this.selectedIbMax - this.selectedIbCount;
    },
    selectedHarvestableCount() {
      if (!this.harvestInfo) {
        return 0;
      }
      return this.harvestInfo.reduce(
        (sum, record) => sum + record.months.length,
        0
      );
    },
    selectedWillingToHarvestCount() {
      if (!this.harvestInfo) {
        return 0;
      }
      return this.harvestInfo.reduce(
        (sum, record) =>
          sum +
          record.months.filter((m) => m >= this.oldestHarvestedMonth).length,
        0
      );
    },
    selectedHarvestablePlatforms() {
      if (!this.harvestInfo) {
        return [];
      }
      let platformMap = new Map();
      this.harvestInfo.forEach((rec) => {
        let arr = platformMap.get(rec.platform) || [];
        arr.push(rec);
        platformMap.set(rec.platform, arr);
      });
      let out = [];
      for (let [platform, records] of platformMap) {
        out.push({
          platform,
          records,
          monthCount: records.reduce(
            (sum, rec) =>
              sum +
              rec.months.filter((m) => m >= this.oldestHarvestedMonth).length,
            0
          ),
        });
      }
      return out.sort((a, b) => a.platform.localeCompare(b.platform));
    },
    selectedCredentialsCount() {
      return this.platformsToHarvest.reduce(
        (out, platform) => out + platform.records.length,
        0
      );
    },
    selectedMonthCount() {
      return this.platformsToHarvest.reduce(
        (out, platform) => out + platform.monthCount,
        0
      );
    },
    compositionBarData() {
      let out = [
        {
          value: this.selectedIbCount / this.selectedIbMax,
          text: this.$tc("months_present", this.selectedIbCount),
          color: "#cef5ce",
        },
        {
          value: this.selectedWillingToHarvestCount / this.selectedIbMax,
          text: this.$tc(
            "months_auto_harvestable",
            this.selectedWillingToHarvestCount
          ),
          color: "#f8e6ac",
        },
        {
          value:
            (this.selectedIbMax -
              this.selectedIbCount -
              this.selectedHarvestableCount) /
            this.selectedIbMax,
          text: this.harvestInfo
            ? this.$tc(
                "months_no_sushi",
                this.selectedIbMax -
                  this.selectedIbCount -
                  this.selectedHarvestableCount
              )
            : this.$t("labels.loading") + "...",
          color: "#d2d2d2",
        },
      ];
      if (this.selectedHarvestableCount > this.selectedWillingToHarvestCount)
        out.splice(2, 0, {
          value:
            (this.selectedHarvestableCount -
              this.selectedWillingToHarvestCount) /
            this.selectedIbMax,
          text: this.$tc(
            "months_harvestable",
            this.selectedHarvestableCount - this.selectedWillingToHarvestCount
          ),
          color: "#fdbfc6",
        });
      return out;
    },
    harvestablePlatformsHeaders() {
      return [
        { text: this.$t("labels.platform"), value: "platform" },
        {
          text: this.$t("labels.credentials"),
          value: "records",
          align: "right",
        },
        {
          text: this.$t("labels.months"),
          value: "monthCount",
          align: "right",
        },
      ];
    },
    oldestHarvestedMonth() {
      return ymDateFormat(counterGuaranteedPeriodStartDate());
    },
    userCanHarvest() {
      return this.showAdminStuff;
    },
  },

  methods: {
    counterVersionToStr(value) {
      return counterVersionToStr(value);
    },
    async fetchReportTypes() {
      let url = "/api/report-type/";
      if (!this.showingAllOrganizations) {
        url = `/api/organization/${this.organizationId}/report-types/used/`;
      }
      let reply = await this.http({
        url: url,
        // undefined values are not sent
        params: {
          "nonzero-only": true,
          start_date: this.dateRangeStart
            ? this.dateRangeStart + "-01"
            : undefined,
          end_date: this.dateRangeCoverageEndText + "-01",
        },
        method: "GET",
      });
      if (!reply.error) {
        this.reportTypes = reply.response.data;
      }
    },
    async fetchTopLevelCoverage(reportType) {
      let extraParams = {};
      if (!this.showingAllOrganizations) {
        extraParams = { organization: this.organizationId };
      }
      return await this.http({
        url: "/api/import-batch/data-coverage/",
        params: {
          report_type: reportType.pk,
          start_date: this.dateRangeStart,
          end_date: this.dateRangeCoverageEndText,
          split_by_date: false,
          ...extraParams,
        },
        method: "GET",
      });
    },
    async fetchHarvestableInfo() {
      // fetches the data for the currently selected report type
      if (!this.selectedReportTypeId) {
        return;
      }
      let extraParams = {};
      if (!this.showingAllOrganizations) {
        extraParams = { organization: this.organizationId };
      }
      const reply = await this.http({
        url: "/api/import-batch/data-coverage-harvestable/",
        params: {
          report_type: this.selectedReportTypeId,
          start_date: this.dateRangeStart,
          end_date: this.dateRangeCoverageEndText,
          ...extraParams,
        },
      });
      if (!reply.error) {
        this.harvestInfo = reply.response.data;
      }
    },
    colorSuccess(value, lighter = false) {
      // using value^3 pushes the color to the red end of the spectrum
      // which is what we need as we want to highlight the low coverage
      const hue = value * value * value * 120;
      if (lighter) {
        return `hsl(${hue}, 50%, 80%)`;
      }
      return `hsl(${hue}, 100%, 40%)`;
    },
    roundValue(value) {
      return Math.floor(value * 100);
    },
    progressByCounterVersion(version) {
      let rts = this.visibleReportTypes.filter(
        (rt) => rt.counter_version === version
      );
      return rts.filter((rt) => !!this.coverageData[rt.pk]).length / rts.length;
    },
    ratioByCounterVersion(version) {
      return this.visibleReportTypes
        .filter((rt) => rt.counter_version === version)
        .reduce(
          (acc, rt) => [
            acc[0] + this.coverageData[rt.pk].ib_max,
            acc[1] + this.coverageData[rt.pk].ib_count,
          ],
          [0, 0]
        )
        .reduce((acc, num) => num / acc, 1);
    },
    async prepare() {
      this.loading = true;
      this.coverageData = {};
      await this.fetchReportTypes();
      for (let reportType of this.visibleReportTypes) {
        // we do this iteratively to avoid overloading the server
        let reply = await this.fetchTopLevelCoverage(reportType);
        if (!reply.error) {
          this.$set(this.coverageData, reportType.pk, reply.response.data[0]);
        }
      }
      if (this.counterVersions.length > 0) {
        this.openedPanel = 0;
      }
      if (
        this.visibleReportTypes
          .map((rt) => rt.pk)
          .includes(this.selectedReportTypeId)
      ) {
        await this.refreshSelectedReportType();
      } else {
        this.selectedReportTypeId = null;
      }
      this.loading = false;
    },
    async refreshSelectedReportType() {
      this.refreshingSelected = true;
      let reply = await this.fetchTopLevelCoverage(this.selectedReportType);
      if (!reply.error) {
        this.$set(
          this.coverageData,
          this.selectedReportType.pk,
          reply.response.data[0]
        );
        this.harvestInfo = null;
        await this.fetchHarvestableInfo();
        if (this.$refs.rtCoverageMap) {
          this.$refs.rtCoverageMap.refresh();
        }
      }
      this.refreshingSelected = false;
    },
    onClick(event) {
      this.selectedPoint = event;
      if (this.showingAllOrganizations) this.showDetailByOrganization = true;
    },
    selectAllPlatforms() {
      this.platformsToHarvest = [...this.selectedHarvestablePlatforms];
    },
    unselectAllPlatforms() {
      this.platformsToHarvest = [];
    },
    async harvestSelected() {
      let intentions = [];
      for (let platformRec of this.platformsToHarvest) {
        for (let credRec of platformRec.records) {
          for (let month of credRec.months.filter(
            (m) => m >= this.oldestHarvestedMonth
          )) {
            intentions.push({
              start_date: month,
              end_date: monthLastDay(parseISO(month)),
              credentials: credRec.credentials_id,
              counter_report: this.selectedReportType.counter_report_type_id,
            });
          }
        }
      }
      this.started = true;

      let reply = await this.http({
        url: "/api/scheduler/harvest/",
        data: {
          intentions: intentions,
        },
        method: "POST",
      });
      if (!reply.error) {
        this.harvestId = reply.response.data.pk;
      }
    },
    rtClick({ reportType }) {
      if (
        this.selectedReportType &&
        this.selectedReportType.pk === reportType.pk
      ) {
        this.refreshSelectedReportType();
      } else {
        this.selectedReportTypeId = reportType.pk;
      }
    },
    onDetailIntersect(entries, observer) {
      this.isDetailVisible = entries[0].isIntersecting;
    },
  },

  async created() {
    await this.prepare();
  },

  watch: {
    organizationId() {
      this.prepare();
    },
    dateRangeStart() {
      this.prepare();
    },
    dateRangeCoverageEndText() {
      this.prepare();
    },
    selectedReportTypeId() {
      this.harvestInfo = null;
      if (this.selectedMissingCount) this.fetchHarvestableInfo();
      // display pulsing button to scroll to the details
      this.$nextTick(() => {
        // we want to give vue time to show the scroll btn
        const btn = document.getElementById("scrollBtn");
        if (btn) btn.classList.add("pulse");
      });
      // deactivate the pulsing after 5 seconds
      setTimeout(() => {
        // we look for the element again as it may have been removed
        // or added in the meantime
        const btn = document.getElementById("scrollBtn");
        if (btn) btn.classList.remove("pulse");
      }, 5000);
    },
    showHarvestDialog() {
      if (!this.showHarvestDialog) {
        // clear the selection upon closing the dialog
        this.platformsToHarvest = [];
        this.harvestId = null;
        // and also re-fetch info about currently selected report type
        // as it may have been updated
        this.refreshSelectedReportType();
      }
    },
  },
};
</script>

<style scoped lang="scss">
.bordered-panel {
  .v-expansion-panel-header {
    border: 1px solid #ddd;
    border-bottom: none;
  }

  .v-expansion-panel-content {
    border-left: 1px solid #ddd;
    border-right: 1px solid #ddd;
  }

  .v-expansion-panel:last-of-type {
    .v-expansion-panel-header {
      border-bottom: 1px solid #ddd;
    }
    .v-expansion-panel-content {
      border-bottom: 1px solid #ddd;
    }
  }
}

.v-card {
  &.selected {
    background-color: #f0f0f0;
  }
}

#scrollBtn {
  display: inline-block;
  background-color: darkorange;
  color: white;
  width: 4rem;
  border-radius: 7px 7px 0 0;
}

.pulse {
  animation: pulse-animation 750ms 5;
}

@keyframes pulse-animation {
  0% {
    box-shadow: 0 0 0 0 rgb(255, 196, 0, 0);
    background-color: #ffc400;
  }
  50% {
    box-shadow: 0 0 0 10px rgb(255, 196, 0, 0.5);
    background-color: darkorange;
  }
  100% {
    box-shadow: 0 0 0 0 rgba(0, 12, 8, 0);
    background-color: #ffc400;
  }
}
</style>
