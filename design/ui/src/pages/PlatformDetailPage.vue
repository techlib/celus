<i18n lang="yaml" src="../locales/charts.yaml"></i18n>
<i18n lang="yaml" src="../locales/common.yaml"></i18n>
<i18n lang="yaml">
en:
  no_info: Unfortunately there are no data about titles available for this platform.
  sushi: Sushi
  raw_export_text: |
    You can export all records stored for this platform in a CSV format.
    The data will be in a raw format very closely matching the structure of the Celus database.
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

cs:
  no_info: Pro tuto platformu bohužel nejsou dostupná žádná data o titulech.
  sushi: Sushi
  raw_export_text: |
    Zde můžete vyexportovat všechna data pro tuto platformu ve formátu CSV.
    Data budou uložena v surové podobě, která blízce odpovídá struktuře databáze Celus.
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
</i18n>

<template>
  <div v-if="loading">
    <LoaderWidget />
  </div>
  <div v-else-if="errorLoadingDetails" class="mt-10 mx-6">
    <ErrorPlaceholder :text="$t('error_loading_data')" />
  </div>
  <div v-else-if="platformDoesNotExist" class="mt-10 mx-6">
    <ErrorPlaceholder :text="$t('platform_does_not_exist')" />
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
          <table v-if="platformObj" class="overview mb-4 elevation-2">
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
          <table v-if="platform" class="overview mb-4 elevation-2">
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
        <v-col cols="auto" v-if="showAdminStuff">
          <v-card>
            <v-card-text>
              <div v-if="organizationSelected && allowManualDataUpload">
                <v-btn
                  text
                  small
                  :to="{
                    name: 'platform-upload-data',
                    params: { platformId: platformId },
                  }"
                >
                  <v-icon small class="mr-2">fa-upload</v-icon>
                  {{ $t("actions.upload_custom_data") }}
                </v-btn>
              </div>
              <div v-if="showAdminStuff">
                <AddAnnotationButton
                  :platform="platformObj"
                  fix-platform
                  @update="refreshAnnotations()"
                  text
                  small
                />
              </div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </v-container>

    <v-alert v-if="unconnectedPlatform" type="warning" outlined>
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

    <v-tabs
      v-model="activeTab"
      background-color="#f5f5f5"
      centered
      grow
      class="mt-1"
    >
      <v-tabs-slider></v-tabs-slider>

      <v-tab href="#chart" v-if="platform">
        <v-icon class="mr-2">fa-chart-bar</v-icon>
        <span v-text="$t('charts')"></span>
      </v-tab>
      <v-tab href="#titles" v-if="platform">
        <v-icon class="mr-2">fa-bars</v-icon>
        <span v-text="$t('titles')"></span>
      </v-tab>
      <v-tab v-if="showAdminStuff && platformObj" href="#sushi">
        <v-icon class="mr-2">fa-download</v-icon>
        <span v-text="$t('sushi')"></span>
      </v-tab>
      <v-tab v-if="showAdminStuff && platform" href="#admin">
        <v-icon class="mr-2">fa-tools</v-icon>
        <span v-text="$t('data_management')"></span>
      </v-tab>

      <v-tabs-items v-model="activeTab" class="platform-page">
        <v-tab-item value="chart">
          <section v-if="selectedOrganizationId && platform">
            <CounterChartSet
              :platform-id="platformId"
              :title-id="null"
              :report-views-url="reportViewsUrl"
              scope="platform"
              ref="chartSet"
            >
            </CounterChartSet>
          </section>
        </v-tab-item>

        <v-tab-item value="titles">
          <section v-if="platform && platform.title_count">
            <InterestGroupSelector />
            <TitleList
              :url="titleListURL"
              :platform-id="platformId"
              :order-interest="orderInterest"
            ></TitleList>
          </section>
          <section v-if="platform && !platform.title_count">
            <v-container fluid>
              <v-alert
                elevation="2"
                colored-border
                border="right"
                type="warning"
                >{{ $t("no_info") }}</v-alert
              >
            </v-container>
          </section>
        </v-tab-item>

        <v-tab-item value="sushi" v-if="showAdminStuff">
          <SushiCredentialsManagementWidget
            :organization-id="this.selectedOrganizationId"
            :platform-id="this.platformId"
          >
          </SushiCredentialsManagementWidget>
        </v-tab-item>

        <v-tab-item value="admin" v-if="showAdminStuff">
          <v-sheet class="ma-1">
            <v-card>
              <v-card-text>
                <v-container class="pa-2 pb-10">
                  <v-row>
                    <v-col>
                      <h3 class="text-h4">{{ $t("labels.data_export") }}</h3>
                    </v-col>
                  </v-row>
                  <v-row>
                    <v-col>
                      <p>{{ $t("raw_export_text") }}</p>
                      <p>
                        <i18n path="raw_export_reporting_link">
                          <template #reporting_module="">
                            <router-link :to="{ name: 'flexitable' }">{{
                              $t("reporting_module")
                            }}</router-link>
                          </template>
                        </i18n>
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

                  <v-row class="pt-4">
                    <v-col>
                      <h3 class="text-h4">{{ $t("labels.delete_data") }}</h3>
                    </v-col>
                  </v-row>

                  <v-row>
                    <v-col>
                      <p>{{ $t("delete_data_text") }}</p>
                    </v-col>
                  </v-row>
                  <v-row no-gutters>
                    <v-col>
                      <DeletePlatformDataWidget
                        :platform="platform"
                        @finished="deleteFinished"
                      />
                    </v-col>
                  </v-row>
                </v-container>
              </v-card-text>
            </v-card>
          </v-sheet>
        </v-tab-item>
      </v-tabs-items>
    </v-tabs>
  </div>
</template>

<script>
import { mapActions, mapGetters, mapState } from "vuex";
import TitleList from "@/components/TitleList";
import axios from "axios";
import CounterChartSet from "@/components/CounterChartSet";
import { formatInteger } from "@/libs/numbers";
import AnnotationsWidget from "@/components/AnnotationsWidget";
import AddAnnotationButton from "@/components/AddAnnotationButton";
import InterestGroupSelector from "@/components/InterestGroupSelector";
import RawDataExportWidget from "@/components/RawDataExportWidget";
import SushiCredentialsManagementWidget from "@/components/sushi/SushiCredentialsManagementWidget";
import DeletePlatformDataWidget from "@/components/admin/DeletePlatformDataWidget";
import ErrorPlaceholder from "@/components/util/ErrorPlaceholder";
import LoaderWidget from "@/components/util/LoaderWidget";

export default {
  name: "PlatformDetailPage",
  components: {
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
      activeTab: this.$route.query.tab || "chart",
      platformNotConnected: false,
      unconnectedPlatform: null, // here we store the platform data if it is not connected
      platformDoesNotExist: false,
      errorLoadingDetails: null,
      loading: false,
    };
  },
  computed: {
    ...mapGetters({
      dateRangeStart: "dateRangeStartText",
      dateRangeEnd: "dateRangeEndText",
      showAdminStuff: "showAdminStuff",
      organizationSelected: "organizationSelected",
      allowManualDataUpload: "allowManualDataUpload",
    }),
    ...mapGetters("interest", {
      activeInterestGroups: "selectedGroupObjects",
    }),
    ...mapState({
      selectedOrganizationId: "selectedOrganizationId",
      interestGroups: (state) => state.interest.interestGroups,
    }),
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
          this.$set(this.platform, "interests", { loading: false });
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
        this.$set(this.platform, "interests", { loading: true });
        try {
          let response = await axios.get(this.platformInterestUrl);
          this.$set(this.platform, "interests", response.data);
        } catch (error) {
          this.showSnackbar({
            content: "Error loading interest: " + error,
            color: "error",
          });
          this.$set(this.platform, "interests", { loading: false });
        }
      }
    },
    async loadPlatformTitleCount() {
      if (this.platformTitleCountUrl) {
        this.$set(this.platform, "title_count", "loading");
        try {
          let response = await axios.get(this.platformTitleCountUrl);
          this.$set(this.platform, "title_count", response.data.title_count);
        } catch (error) {
          this.showSnackbar({
            content: "Error loading title count: " + error,
            color: "error",
          });
          this.$set(this.platform, "title_count", null);
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
    deleteFinished({ platformId }) {
      if (platformId === this.platformId) {
        this.loadPlatform();
      }
    },
  },
  created() {
    this.loadPlatform();
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
    activeTab() {
      if (this.activeTab === "chart" && this.$refs.chartSet) {
        this.$refs.chartSet.reloadChartData();
      }
    },
  },
};
</script>

<style lang="scss">
.thin {
  font-weight: 300;
}

table.overview {
  padding: 1rem;

  tr.header {
    th {
      font-variant: small-caps;
      font-weight: 500;
      font-size: 82.5%;
      border-bottom: solid 1px #dddddd;
      padding-top: 0.5rem;
    }
    &:first-child {
      th {
        padding-top: 0;
      }
    }
  }

  th {
    text-align: left;
    padding-right: 1.5rem;
    font-weight: 300;

    &.subdued-th {
      //font-weight: normal;
      color: #999999;
    }
  }
}

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
</style>
