<i18n lang="yaml" src="@/locales/charts.yaml"></i18n>

<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<i18n lang="yaml">
en:
  no_info: Unfortunately there are no data about titles available for this platform.
  sushi: Sushi
  raw_export_text: |
    You can export all records stored for this platform in a CSV format.
    The data will be in a raw format very closely matching the structure of the CELUS database.
    The format is not suitable for reporting, but rather for further machine processing.
  raw_export_reporting_link: For smarter and very configurable data export use the {reporting_module}.
  reporting_module: Reporting module
  data_management: Data management
  delete_data_text: |
    If you for some reason need to delete all data for this platform, you can do it using the button below.
    It will remove all the harvested and/or manually uploaded usage data. If you have
    SUSHI credentials present, they will be preserved to allow you subsequent reharvesting of the data.
    Also any harvests planned for the future will be preserved and run at their assigned time.
  error_loading_data: There was an error loading data for this platform.
  platform_does_not_exist: Sorry, such platform does not exist.
  unconnected_platform: |
    The platform "{platform}" is not associated with the selected organization. To be able to
    display usage data for you, you need to create SUSHI credentials for this platform or manually
    upload some data for it.
  counter_data_export_text: Here you can download generated COUNTER reports directly from CELUS. The data are filtered based on selected organization and date range in the page header.
  counter_data_export_no_org: No organization is selected, please select an organization from the top bar in order to download data in COUNTER format.
  curve_info: |
    The following curve describes on which day of month SUSHI data
    typically become available on this platform (a generic curve is
    used when not enough data is present for a platform). CELUS uses
    this information to plan automatic harvesting in order to minimize
    delay, but maximize chance of success.
  curve_title: SUSHI data availability curve
  stats_for_geeks: Stats for geeks
  curve_attempts_info: The arrows shown on the curve show the typical points when CELUS will attempt to (re)harvest data for this platform. The actual dates may vary slightly to accommodate internal rules and potential manual harvests.

cs:
  no_info: Pro tuto platformu bohužel nejsou dostupná žádná data o titulech.
  sushi: Sushi
  raw_export_text: |
    Zde můžete vyexportovat všechna data pro tuto platformu ve formátu CSV.
    Data budou uložena v surové podobě, která blízce odpovídá struktuře databáze CELUS.
    Formát není vhodný pro přímý reporting, hodí se zejména pro další strojové zpracování.
  raw_export_reporting_link: Pro chytřejší a vysoce konfigurovatelný export doporučujeme {reporting_module}.
  reporting_module: modul Reporting
  data_management: Správa dat
  delete_data_text: |
    Pokud z nějakého důvodu potřebujete smazat všechna data pro tuto platformu, můžete použít tlačítko níže.
    Smažete tak všechna stažená a/nebo ručně nahraná data o využívanosti. Pokud máte pro platformu
    uloženy přihlašovací údaje pro SUSHI, budou zachována pro případné následné stažení nových dat.
    Také sklízení dat naplánované do budoucnosti bude zachováno a spouštěno ve stanoveném čase.
  error_loading_data: Při přípravě informací o této platformě došlo k chybě.
  platform_does_not_exist: Je nám líto, ale taková platofma neexistuje.
  unconnected_platform: |
    Platforma "{platform}" není přiřazená k právě vybrané instituci. Abychom vám pro ni mohli zobrazit data,
    je třeba pro ni nejprve přidat přihlašovací údaje SUSHI a nebo manuálně nahrát data.
  counter_data_export_text: Zde si stáhnout vygenerované COUNTER reporty přímo z CELUSu.  Data jsou filtrováná podle zvolené organizace a rozmezí dat v hlavičce stránky.
  counter_data_export_no_org: Není vybraná oranizace, prosím vyberte organizaci v horním panelu, aby bylo možné stáhnout data v COUNTER formátu.
  curve_info: |
    Následující křivka popisuje, ve kolikátý den v měsíci jsou obvykle dostupná SUSHI data
    pro tuto platformu (pokud není dostatek dat pro konkrétní platformu, použije se obecná křivka).
    CELUS tuto informaci využívá pro plánování automatického sklízení dat tak, aby minimalizoval
    zpoždění, ale zároveň maximalizoval šanci na úspěch.
  curve_title: Křivka dostupnosti dat pro SUSHI
  stats_for_geeks: Statistiky pro nadšence
  curve_attempts_info: Šipky na křivce ukazují typické body, kdy se CELUS bude pokoušet (znovu)stáhnout data pro tuto platformu. Skutečné časy se mohou mírně lišit kvůli interním pravidlů a jsou ovlivněny případnými manuálními staženími.
</i18n>

<template>
  <div v-if="loading">
    <LoaderWidget></LoaderWidget>
  </div>
  <div v-else-if="errorLoadingDetails" class="mt-10 mx-6">
    <ErrorPlaceholder :text="$t('error_loading_data')"></ErrorPlaceholder>
  </div>
  <div v-else-if="platformDoesNotExist" class="mt-10 mx-6">
    <ErrorPlaceholder :text="$t('platform_does_not_exist')"></ErrorPlaceholder>
  </div>
  <div v-else class="px-md-2">
    <div>
      <v-breadcrumbs :items="breadcrumbs" class="pl-0">
        <template v-slot:item="props">
          <router-link
            v-if="props.item.linkName"
            :to="{ name: props.item.linkName, params: props.item.linkParams }"
          >
            {{ props.item.text }}
          </router-link>
          <span v-else>
            {{ props.item.text }}
          </span>
        </template>
      </v-breadcrumbs>
    </div>
    <h2 class="mb-0">{{ platformObj ? platformObj.name : "" }}</h2>
    <v-container fluid class="px-0">
      <v-row>
        <v-col cols="auto" mr-sm-4>
          <table v-if="platformObj" class="overview-card mb-4 elevation-2">
            <tr>
              <th>{{ $t("labels.provider") }}</th>
              <td>{{ platformObj.provider }}</td>
            </tr>
            <tr>
              <th>{{ $t("labels.url") }}</th>
              <td>
                <a :href="platformObj.url">{{ platformObj.url }}</a>
              </td>
            </tr>
          </table>
        </v-col>
        <v-col cols="auto" mr-sm-4>
          <table v-if="platform" class="overview-card mb-4 elevation-2">
            <tr>
              <th>{{ $t("labels.title_count") }}</th>
              <td class="text-right">
                <span
                  v-if="platform.title_count === 'loading'"
                  class="fas fa-spinner fa-spin subdued"
                >
                </span>
                <span v-else>
                  {{ formatInteger(platform.title_count) }}
                </span>
              </td>
            </tr>
            <tr class="header">
              <th colspan="2" v-text="$t('interest')"></th>
            </tr>
            <tr v-for="ig in interestGroups" :key="ig.pk">
              <th
                v-text="ig.name"
                :class="{
                  'subdued-th':
                    platform.interests.loading ||
                    platform.interests[ig.short_name] === 0,
                }"
              ></th>
              <td class="text-right">
                <span
                  v-if="platform.interests.loading"
                  class="fas fa-spinner fa-spin subdued"
                >
                </span>
                <span
                  v-else
                  :class="{ subdued: platform.interests[ig.short_name] === 0 }"
                >
                  {{ formatInteger(platform.interests[ig.short_name]) }}
                </span>
              </td>
            </tr>
          </table>
        </v-col>
        <v-spacer></v-spacer>
        <v-col cols="auto">
          <TagCard scope="platform" :item-id="platformId"></TagCard>
        </v-col>
        <v-col cols="auto" v-if="showAdminStuff">
          <v-card>
            <v-card-text>
              <div>
                <v-btn
                  variant="text"
                  size="small"
                  :to="{
                    name: 'platform-upload-data',
                    params: { platformId: platformId },
                  }"
                >
                  <v-icon size="small" class="mr-2">fa fa-upload</v-icon>
                  {{ $t("actions.upload_data") }}
                </v-btn>
              </div>
              <div v-if="showAdminStuff">
                <AddAnnotationButton
                  :platform="platformObj"
                  fix-platform
                  @update="refreshAnnotations()"
                  text
                  small
                ></AddAnnotationButton>
              </div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </v-container>
    <v-alert v-if="unconnectedPlatform" type="warning" variant="outlined">
      {{ $t("unconnected_platform", { platform: unconnectedPlatform.name }) }}
    </v-alert>
    <section class="mb-5" v-if="platformObj">
      <AnnotationsWidget
        :platform="platformObj"
        :allow-add="showAdminStuff"
        fix-platform
        ref="annotWidget"
      >
      </AnnotationsWidget>
    </section>
    <v-card>
      <v-tabs
        v-model="activeTab"
        bg-color="#f5f5f5"
        centered
        grow
        class="mt-1"
        color="#2d5854"
      >
        <v-tab value="chart" v-if="platform">
          <v-icon class="mr-2">fas fa-chart-bar</v-icon>
          <span>{{ $t("charts") }}</span>
        </v-tab>
        <v-tab value="titles" v-if="platform">
          <v-icon class="mr-2">fa fa-bars</v-icon>
          <span>{{ $t("titles") }}</span>
        </v-tab>
        <v-tab value="coverage" v-if="platform">
          <v-icon class="mr-2">fas fa-layer-group</v-icon>
          <span>{{ $t("series.data_coverage") }}</span>
        </v-tab>
        <v-tab v-if="showAdminStuff && platformObj" value="sushi">
          <v-icon class="mr-2">fa fa-download</v-icon>
          <span>{{ $t("sushi") }}</span>
        </v-tab>
        <v-tab v-if="showAdminStuff && platform" value="admin">
          <v-icon class="mr-2">fas fa-tools</v-icon>
          <span>{{ $t("data_management") }}</span>
        </v-tab>
      </v-tabs>
      <v-window v-model="activeTab" class="platform-page">
        <v-window-item value="chart">
          <section v-if="selectedOrganizationId && platform" class="px-4">
            <CounterChartSet
              :platform-id="platformId"
              :title-id="null"
              :report-views-url="reportViewsUrl"
              scope="platform"
              ref="chartSet"
            >
            </CounterChartSet>
          </section>
        </v-window-item>
        <v-window-item value="titles">
          <section v-if="platform && platform.title_count">
            <InterestGroupSelector class="px-4"></InterestGroupSelector>
            <TitleList
              class="px-4"
              :url="titleListURL"
              :platform-id="platformId"
              :order-interest="orderInterest"
              @goto-sushi="goToSushi"
            ></TitleList>
          </section>
          <section v-if="platform && !platform.title_count">
            <v-container fluid class="px-4">
              <v-alert elevation="2" border="end" type="warning" border-color>{{
                $t("no_info")
              }}</v-alert>
            </v-container>
          </section>
        </v-window-item>
        <v-window-item value="coverage">
          <section v-if="platform">
            <CoverageOverviewWidget
              :platform-id="platformId"
            ></CoverageOverviewWidget>
          </section>
        </v-window-item>
        <v-window-item value="sushi" v-if="showAdminStuff">
          <SushiCredentialsManagementWidget
            :organization-id="this.selectedOrganizationId"
            :platform-id="this.platformId"
          >
          </SushiCredentialsManagementWidget>
          <div class="ma-3">
            <v-expansion-panels>
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <span>
                    <v-icon class="mr-2" size="x-small">fa fa-chart-bar</v-icon>
                    <span class="font-weight-medium small-caps">{{
                      $t("stats_for_geeks")
                    }}</span>
                  </span>
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <h3 class="text-h5 pb-3">{{ $t("curve_title") }}</h3>
                  <p>{{ $t("curve_info") }}</p>
                  <div>
                    <v-switch
                      v-model="showAttemptsOnCurve"
                      label="Show attempts"
                    ></v-switch>
                  </div>
                  <SushiArrivalCurve
                    v-if="platform"
                    :stats="platform.sushi_arrival_stats"
                    :show-title="false"
                    :highlight-probas="havestingProbabilities"
                  ></SushiArrivalCurve>
                  <p v-if="showAttemptsOnCurve">
                    {{ $t("curve_attempts_info") }}
                  </p>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>
          </div>
        </v-window-item>
        <v-window-item value="admin" v-if="showAdminStuff">
          <v-sheet class="ma-1">
            <v-card>
              <v-card-text>
                <v-container class="pa-2 pb-2">
                  <section v-if="showAdminStuff" class="pb-8">
                    <!-- raw data export -->
                    <v-row>
                      <v-col>
                        <h3 class="text-h4 label_admin">
                          {{ $t("labels.data_export") }}
                        </h3>
                      </v-col>
                    </v-row>
                    <v-row>
                      <v-col>
                        <p class="admin_tab">{{ $t("raw_export_text") }}</p>
                        <p class="admin_tab">
                          <i18n-t keypath="raw_export_reporting_link">
                            <template #reporting_module>
                              <router-link :to="{ name: 'flexitable' }">{{
                                $t("reporting_module")
                              }}</router-link>
                            </template>
                          </i18n-t>
                        </p>
                      </v-col>
                    </v-row>
                    <v-row no-gutters>
                      <v-col>
                        <raw-data-export-widget
                          color="primary"
                          :platform="platformId"
                        ></raw-data-export-widget>
                      </v-col>
                    </v-row>
                  </section>
                  <section v-if="clickhouseQueryActive" class="pt-4 pb-8">
                    <!-- counter data export -->
                    <v-row>
                      <v-col>
                        <h3 class="text-h4 label_admin">
                          {{ $t("labels.counter_data_export") }}
                        </h3>
                        <v-alert
                          v-if="(selectedOrganizationId || 0) <= 0"
                          class="mt-2 mb-1"
                          type="warning"
                          variant="outlined"
                        >
                          <p class="mb-0">
                            {{ $t("counter_data_export_no_org") }}
                          </p>
                        </v-alert>
                      </v-col>
                    </v-row>
                    <v-row>
                      <v-col>
                        <p class="admin_tab">
                          {{ $t("counter_data_export_text") }}
                        </p>
                      </v-col>
                    </v-row>
                    <v-row no-gutters>
                      <v-table>
                        <tbody>
                          <tr>
                            <th>COUNTER 5.1</th>
                            <td
                              v-for="item in exportableCounterReportTypes51"
                              :key="item.id"
                            >
                              <CounterDataExportWidget
                                v-if="item"
                                :platform="platformObj"
                                :counter-report-type="item"
                              />
                            </td>
                          </tr>
                          <tr>
                            <th>COUNTER 5</th>
                            <td
                              v-for="item in exportableCounterReportTypes5"
                              :key="item.pk"
                            >
                              <CounterDataExportWidget
                                v-if="item"
                                :platform="platformObj"
                                :counter-report-type="item"
                              />
                            </td>
                          </tr>
                        </tbody>
                      </v-table>
                    </v-row>
                  </section>
                  <section v-if="showAdminStuff" class="pt-4 pb-8">
                    <!-- delete data -->
                    <v-row>
                      <v-col>
                        <h3 class="text-h4 label_admin">
                          {{ $t("labels.delete_data") }}
                        </h3>
                      </v-col>
                    </v-row>
                    <v-row>
                      <v-col>
                        <p class="admin_tab">{{ $t("delete_data_text") }}</p>
                      </v-col>
                    </v-row>
                    <v-row no-gutters>
                      <v-col>
                        <DeletePlatformDataWidget
                          :platform="platform"
                          @finished="deleteFinished"
                        ></DeletePlatformDataWidget>
                      </v-col>
                    </v-row>
                  </section>
                </v-container>
              </v-card-text>
            </v-card>
          </v-sheet>
        </v-window-item>
      </v-window>
    </v-card>
  </div>
</template>

<script>
import { mapActions, mapGetters, mapState } from "vuex";
import TitleList from "@/components/TitleList";
import axios from "axios";
import CounterChartSet from "@/components/charts/CounterChartSet";
import { formatInteger } from "@/libs/numbers";
import AnnotationsWidget from "@/components/AnnotationsWidget";
import AddAnnotationButton from "@/components/AddAnnotationButton";
import CounterDataExportWidget from "@/components/CounterDataExportWidget";
import InterestGroupSelector from "@/components/selectors/InterestGroupSelector";
import RawDataExportWidget from "@/components/RawDataExportWidget";
import SushiCredentialsManagementWidget from "@/components/sushi/SushiCredentialsManagementWidget";
import DeletePlatformDataWidget from "@/components/admin/DeletePlatformDataWidget";
import ErrorPlaceholder from "@/components/util/ErrorPlaceholder";
import LoaderWidget from "@/components/util/LoaderWidget";
import TagCard from "@/components/tags/TagCard";
import CoverageOverviewWidget from "@/components/charts/CoverageOverviewWidget";
import SushiArrivalCurve from "@/components/charts/SushiArrivalCurve.vue";
import stateTracking from "@/mixins/stateTracking";

export default {
  name: "PlatformDetailPage",

  mixins: [stateTracking],

  components: {
    SushiArrivalCurve,
    CounterDataExportWidget,
    CoverageOverviewWidget,
    TagCard,
    LoaderWidget,
    ErrorPlaceholder,
    DeletePlatformDataWidget,
    SushiCredentialsManagementWidget,
    TitleList,
    CounterChartSet,
    AnnotationsWidget,
    AddAnnotationButton,
    InterestGroupSelector,
    RawDataExportWidget,
  },

  props: {
    platformId: { required: true },
  },

  data() {
    return {
      platform: null,
      activeTab: "chart",
      platformNotConnected: false,
      unconnectedPlatform: null, // here we store the platform data if it is not connected
      platformDoesNotExist: false,
      errorLoadingDetails: null,
      loading: false,
      counterReportTypes: [],
      loadingCounterReportTypes: false,
      watchedAttrs: [{ name: "activeTab", type: String, var: "tab" }],
      showAttemptsOnCurve: false,
      counterExportTab: null,
    };
  },
  computed: {
    ...mapGetters({
      dateRangeStart: "dateRangeStartText",
      dateRangeEnd: "dateRangeEndText",
      showAdminStuff: "showAdminStuff",
      organizationSelected: "organizationSelected",
      clickhouseQueryActive: "clickhouseQueryActive",
      enableItems: "enableItems",
    }),
    ...mapGetters("interest", {
      activeInterestGroups: "selectedGroupObjects",
    }),
    ...mapState({
      selectedOrganizationId: "selectedOrganizationId",
      basicInfo: "basicInfo",
      interestGroups: (state) => state.interest.interestGroups,
    }),
    havestingProbabilities() {
      return this.showAttemptsOnCurve
        ? this.basicInfo.AUTO_HARVESTING_PROBABILITIES
        : [];
    },
    titleListURL() {
      if (this.platform !== null) {
        return `/api/organization/${this.selectedOrganizationId}/platform/${this.platform.pk}/title-interest/?start=${this.dateRangeStart}&end=${this.dateRangeEnd}`;
      }
      return null;
    },
    reportViewsUrl() {
      if (this.selectedOrganizationId && this.platformId) {
        return `/api/organization/${this.selectedOrganizationId}/platform/${this.platformId}/report-views/`;
      }
      return null;
    },
    platformInterestUrl() {
      if (this.selectedOrganizationId) {
        return `/api/organization/${this.selectedOrganizationId}/platform-interest/${this.platformId}/?start=${this.dateRangeStart}&end=${this.dateRangeEnd}`;
      }
      return null;
    },
    platformTitleCountUrl() {
      if (this.selectedOrganizationId) {
        return `/api/organization/${this.selectedOrganizationId}/platform/${this.platformId}/title-count/?start=${this.dateRangeStart}&end=${this.dateRangeEnd}`;
      }
      return null;
    },
    platformDetailUrl() {
      if (this.selectedOrganizationId) {
        return `/api/organization/${this.selectedOrganizationId}/platform/${this.platformId}/`;
      }
      return null;
    },
    counterReportTypeUsedUrl() {
      let url = `/api/counter-data-export/used/`;
      url += `?platform=${this.platformId}`;
      url += `&organization=${this.selectedOrganizationId || 0}`;
      if (this.dateRangeStart) {
        url += `&start_date=${this.dateRangeStart}`;
      }
      if (this.dateRangeEnd) {
        url += `&end_date=${this.dateRangeEnd}`;
      }
      return url;
    },
    unconnectedPlatformDetailUrl() {
      if (this.selectedOrganizationId) {
        return `/api/organization/${this.selectedOrganizationId}/all-platform/${this.platformId}/`;
      }
      return null;
    },
    breadcrumbs() {
      return [
        {
          text: this.$t("pages.platforms"),
          linkName: "platform-list",
        },
        {
          text:
            this.platform === null
              ? this.unconnectedPlatform
                ? this.unconnectedPlatform.name
                : ""
              : this.platform.name,
        },
      ];
    },
    orderInterest() {
      // The interest that should be used for sorting the titles
      if (this.activeInterestGroups.length) {
        return this.activeInterestGroups[0].short_name;
      }
      return null;
    },
    platformObj() {
      return this.platform || this.unconnectedPlatform;
    },
    exportableReportCodes() {
      let out = ["PR", "DR", "TR", "IR_M1"];
      if (this.enableItems) {
        out.splice(out.indexOf("IR_M1"), 0, "IR");
      }
      return out;
    },
    exportableCounterReportTypes5() {
      return this.exportableCounterReportTypes(5);
    },
    exportableCounterReportTypes51() {
      return this.exportableCounterReportTypes(51);
    },
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    formatInteger: formatInteger,
    async loadPlatform() {
      if (this.platformDetailUrl) {
        this.loading = true;
        try {
          let response = await axios.get(this.platformDetailUrl);
          this.platform = response.data;
          this.platform.interests = { loading: false };
          await Promise.all([
            this.loadPlatformTitleCount(),
            this.loadPlatformInterest(),
          ]);
        } catch (error) {
          if (error.response?.status === 404) {
            // the platform is not available, but this may be that it is just
            // not connected to the current organization
            if (this.organizationSelected) {
              await this.loadUnconnectedPlatform();
            } else {
              this.platformDoesNotExist = true;
            }
          } else {
            this.showSnackbar({ content: "Error loading platforms: " + error });
            this.errorLoadingDetails = error;
          }
        } finally {
          this.loading = false;
        }
      }
    },
    async loadPlatformInterest() {
      if (this.platformInterestUrl) {
        this.platform.interests = { loading: true };
        try {
          let response = await axios.get(this.platformInterestUrl);
          this.platform.interests = response.data;
        } catch (error) {
          this.showSnackbar({
            content: "Error loading interest: " + error,
            color: "error",
          });
          this.platform.interests = { loading: false };
        }
      }
    },
    async loadPlatformTitleCount() {
      if (this.platformTitleCountUrl) {
        this.platform.title_count = "loading";
        try {
          let response = await axios.get(this.platformTitleCountUrl);
          this.platform.title_count = response.data.title_count;
        } catch (error) {
          this.showSnackbar({
            content: "Error loading title count: " + error,
            color: "error",
          });
          this.platform.title_count = null;
        }
      }
    },
    refreshAnnotations() {
      this.$refs.annotWidget.fetchAnnotations();
    },
    async loadUnconnectedPlatform() {
      if (this.unconnectedPlatformDetailUrl) {
        try {
          let response = await axios.get(this.unconnectedPlatformDetailUrl);
          this.unconnectedPlatform = response.data;
        } catch (error) {
          if (error.response?.status === 404) {
            // the platform is not available
            this.platformDoesNotExist = true;
          } else {
            this.showSnackbar({ content: "Error loading platforms: " + error });
            this.errorLoadingDetails = error;
          }
        }
      }
    },
    async deleteFinished({ platformId, platformDeleted }) {
      if (platformId === this.platformId) {
        if (platformDeleted) {
          await this.$router.push({ name: "platform-list", replace: true });
        } else {
          this.loadPlatform();
        }
      }
    },
    async loadCounterReportTypes() {
      this.loadingCounterReportTypes = true;
      try {
        let result = await axios.get(this.counterReportTypeUsedUrl);
        this.counterReportTypes = result.data;
      } catch (error) {
        this.showSnackbar({ content: "Error loading report types: " + error });
      } finally {
        this.loadingCounterReportTypes = false;
      }
    },
    goToSushi() {
      this.activeTab = "sushi";
    },
    exportableCounterReportTypes(version) {
      let out = [];
      const candidates = this.counterReportTypes.filter(
        (e) => e.counter_version === version,
      );
      this.exportableReportCodes.forEach((code) => {
        let crt = candidates.find((e) => e.code === code);
        if (crt) {
          out.push(crt);
        }
      });
      return out;
    },
  },
  created() {
    this.loadPlatform();
    this.loadCounterReportTypes();
  },
  watch: {
    platformDetailUrl() {
      this.loadPlatform();
    },
    platformInterestUrl() {
      this.loadPlatformInterest();
    },
    platformTitleCountUrl() {
      this.loadPlatformTitleCount();
    },
    counterReportTypeUsedUrl() {
      this.loadCounterReportTypes();
    },
    activeTab() {
      if (this.activeTab === "chart" && this.$refs.chartSet) {
        this.$refs.chartSet.reloadReportViews();
        this.$refs.chartSet.reloadChartData();
      } else if (this.activeTab === "admin") {
        this.loadCounterReportTypes();
      }
    },
  },
};
</script>

<style lang="scss">
.v-tab--active {
  background-color: #e0f2f1aa;
}

hr.light {
  color: #ffffff;
  background-color: #00a000;
}

.v-tabs-items {
  &.platform-page {
    min-height: 600px;
  }
}

.admin_tab {
  color: rgba(0, 0, 0, 0.6);
  margin-bottom: 16px;
}

.label_admin {
  color: rgba(0, 0, 0, 0.6);
}

/* .tab-active {
  color: #2d5854 !important;
}

.tab-inactive {
  color: #0000008a !important;
} */
</style>
