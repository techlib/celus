<i18n lang="yaml" src="@/locales/charts.yaml"></i18n>
<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<i18n lang="yaml">
en:
  available_from_platforms: Available from platforms
  this_title_on_platform: Link to this title on the selected platform
  this_title_no_platform: Link to all data for this title without platform filter
  current_platform: Current platform
  no_platform: Regardless of platform
  not_available_from_any_platform: This title did not appear on any platform in the selected time period.
  try_larger_window: Try selecting a broader date range.
cs:
  available_from_platforms: Dostupné na platformách
  this_title_on_platform: Odkaz na tento titul na uvedené platformě
  this_title_no_platform: Odkaz na souhrná data pro tento titul bez ohledu na platformu
  current_platform: Právě zobrazovaná platforma
  no_platform: Bez ohledu na platformu
  not_available_from_any_platform: Tento titul se v zvoleném časovém období neobjevil na žádné platformě.
  try_larger_window: Zkuste vybrat širší časové období.
</i18n>

<template>
  <v-container fluid class="ml-0 px-2 px-sm-2">
    <v-row no-gutters>
      <v-col>
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
      </v-col>
    </v-row>
    <v-row class="d-none d-sm-block">
      <v-col>
        <h2 class="mb-sm-2">{{ titleName }}</h2>
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="auto">
        <table class="overview-card elevation-2">
          <tr v-if="this.platformId">
            <th>{{ $t("platform") }}</th>
            <td>{{ platformName }}</td>
          </tr>
          <tr>
            <th>{{ $t("title") }}</th>
            <td>{{ titleName }}</td>
          </tr>
          <template v-if="title">
            <tr
              v-for="(prop, index) in ['isbn', 'issn', 'eissn', 'doi']"
              :key="index"
            >
              <th>{{ $t("title_fields." + prop) }}</th>
              <td>{{ title[prop] }}</td>
            </tr>
          </template>
        </table>
      </v-col>
      <v-col cols="auto" v-if="title">
        <table class="overview-card elevation-2">
          <tr class="header">
            <th colspan="2" v-text="$t('interest')"></th>
          </tr>
          <tr v-for="ig in interestGroups" :key="ig.short_name">
            <th
              v-text="ig.name"
              :class="{
                'subdued-th':
                  interestsLoading || interests[ig.short_name] === 0,
              }"
            ></th>
            <td class="text-right">
              <span
                v-if="interestsLoading"
                class="fas fa-spinner fa-spin subdued"
              >
              </span>
              <span v-else :class="{ subdued: interests[ig.short_name] === 0 }">
                {{ formatInteger(interests[ig.short_name]) }}
              </span>
            </td>
          </tr>
        </table>
      </v-col>
      <v-col cols="auto" v-if="availableFromPlatforms">
        <table class="overview-card elevation-2">
          <tr class="header">
            <th colspan="2" v-text="$t('available_from_platforms')"></th>
          </tr>
          <tr v-if="availableFromPlatforms.length === 0">
            <td
              class="text-caption pt-3"
              @mouseenter="changeDateSelectorHighlight({ highlight: true })"
              @mouseleave="changeDateSelectorHighlight({ highlight: false })"
            >
              <div>
                <v-icon x-small color="warning" class="mb-1"
                  >fa-exclamation-triangle</v-icon
                >
                {{ $t("not_available_from_any_platform") }}
              </div>
              <div v-if="hasInterestOutsideOfTimeRange">
                {{ $t("try_larger_window") }}
              </div>
            </td>
          </tr>
          <tr v-for="platform in availableFromPlatforms" :key="platform.pk">
            <td>
              <router-link
                :to="{
                  name: 'platform-detail',
                  params: { platformId: platform.pk },
                }"
              >
                {{ platform.name }}
              </router-link>
            </td>
            <td class="text-right">
              <v-tooltip bottom v-if="platform.pk !== platformId">
                <template v-slot:activator="{ on }">
                  <v-btn
                    small
                    icon
                    v-on="on"
                    color="secondary"
                    :to="{
                      name: 'platform-title-detail',
                      params: { platformId: platform.pk, titleId: titleId },
                    }"
                  >
                    <v-icon small>fa-external-link-alt</v-icon>
                  </v-btn>
                </template>
                <span v-text="$t('this_title_on_platform')"></span>
              </v-tooltip>
              <v-tooltip bottom v-else>
                <template v-slot:activator="{ on }">
                  <span v-on="on">
                    <v-btn small icon color="secondary" disabled>
                      <v-icon small>fa-arrow-left</v-icon>
                    </v-btn>
                  </span>
                </template>
                <span v-text="$t('current_platform')"></span>
              </v-tooltip>
            </td>
          </tr>

          <tr
            v-if="
              platformId &&
              availableFromPlatforms &&
              availableFromPlatforms.length > 1
            "
            class="mt-4"
          >
            <!-- if platform is specified, we provide a link to this title without platform specified -->
            <td v-text="$t('no_platform')" class="pt-4 font-weight-light"></td>
            <td class="text-right pt-4">
              <v-tooltip bottom>
                <template v-slot:activator="{ on }">
                  <v-btn
                    small
                    icon
                    v-on="on"
                    color="secondary"
                    :to="{
                      name: 'title-detail',
                      params: { platformId: null, titleId: titleId },
                    }"
                  >
                    <v-icon small>fa-external-link-alt</v-icon>
                  </v-btn>
                </template>
                <span v-text="$t('this_title_no_platform')"></span>
              </v-tooltip>
            </td>
          </tr>
        </table>
      </v-col>
      <v-spacer></v-spacer>
      <v-col cols="12" sm="6" md="4" lg="3">
        <TagCard v-if="titleId" scope="title" :item-id="titleId" show-class />
      </v-col>
    </v-row>

    <section class="my-4" id="annotations">
      <AnnotationsWidget
        v-if="platformData"
        :platform="platformData"
        @loaded="annotationsLoaded"
      ></AnnotationsWidget>
    </section>

    <section v-if="isReady">
      <v-row>
        <v-col>
          <h3>{{ $t("overview") }}</h3>
        </v-col>
        <v-col cols="auto">
          <data-export-widget :title="titleId" :platform="platformId">
          </data-export-widget>
        </v-col>
      </v-row>

      <CounterChartSet
        :platform-id="platformId"
        :title-id="titleId"
        :report-views-url="reportViewsUrl"
        scope="title"
      >
      </CounterChartSet>
    </section>
  </v-container>
</template>

<script>
import { mapActions, mapGetters, mapState } from "vuex";
import CounterChartSet from "@/components/charts/CounterChartSet";
import DataExportWidget from "@/components/DataExportWidget";
import AnnotationsWidget from "@/components/AnnotationsWidget";
import goTo from "vuetify/es5/services/goto";
import { formatInteger } from "@/libs/numbers";
import cancellation from "@/mixins/cancellation";
import TagCard from "@/components/tags/TagCard";

export default {
  name: "TitleDetailPage",
  components: {
    TagCard,
    DataExportWidget,
    CounterChartSet,
    AnnotationsWidget,
  },
  mixins: [cancellation],
  props: {
    platformId: { required: false, type: Number },
    titleId: { required: true, type: Number },
  },
  data() {
    return {
      title: null,
      interests: {},
      interestsLoading: false,
      platformData: null,
      annotationsCount: 0,
      availableFromPlatforms: null,
      hasInterestOutsideOfTimeRange: false,
    };
  },
  computed: {
    ...mapState({
      interestGroups: (state) => state.interest.interestGroups,
    }),
    ...mapGetters({
      selectedOrganization: "selectedOrganization",
      dateRangeStart: "dateRangeStartText",
      dateRangeEnd: "dateRangeEndText",
    }),
    isReady() {
      return this.selectedOrganization && this.titleId;
    },
    platform() {
      return this.platformData;
    },
    platformName() {
      if (this.platform) {
        return this.platform.name;
      }
      return "";
    },
    titleName() {
      if (this.title) {
        return this.title.name;
      }
      return "";
    },
    breadcrumbs() {
      if (this.platformId) {
        return [
          {
            text: this.$t("pages.platforms"),
            linkName: "platform-list",
          },
          {
            text: this.platformName,
            linkName: "platform-detail",
            linkParams: {
              platformId: this.platformId,
            },
          },
          {
            text: this.titleName,
          },
        ];
      }
      return [
        {
          text: this.$t("titles"),
          linkName: "title-list",
        },
        {
          text: this.titleName,
        },
      ];
    },
    titleInterestUrl() {
      if (this.titleInterestUrlNoDates) {
        return `${this.titleInterestUrlNoDates}?start=${this.dateRangeStart}&end=${this.dateRangeEnd}`;
      }
      return null;
    },
    titleInterestUrlNoDates() {
      if (this.selectedOrganization && this.titleId) {
        if (this.platformId) {
          return `/api/organization/${this.selectedOrganization.pk}/platform/${this.platformId}/title-interest/${this.titleId}/`;
        } else {
          // this is the case when no platform is specified
          return `/api/organization/${this.selectedOrganization.pk}/title-interest/${this.titleId}/`;
        }
      }
      return null;
    },
    titleUrl() {
      if (this.titleId) {
        return `/api/title/${this.titleId}/`;
      }
      return null;
    },
    reportViewsUrl() {
      if (this.selectedOrganization && this.titleId) {
        if (this.platformId) {
          return `/api/organization/${this.selectedOrganization.pk}/platform/${this.platformId}/title/${this.titleId}/report-views/`;
        } else {
          // this is the case when no platform is specified
          return `/api/organization/${this.selectedOrganization.pk}/title/${this.titleId}/report-views/`;
        }
      }
      return null;
    },
    isMaxDateRange() {
      return !this.dateRangeStart && !this.dateRangeEnd;
    },
    selectedOrganizationId() {
      return this.selectedOrganization.pk;
    },
  },
  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
      changeDateSelectorHighlight: "changeDateSelectorHighlight",
    }),
    goTo: goTo,
    formatInteger: formatInteger,
    async loadTitle() {
      if (this.titleUrl) {
        const result = await this.http({ url: this.titleUrl });
        if (!result.error) {
          this.title = result.response.data;
          await this.loadInterest();
        }
      }
    },
    async loadInterest() {
      if (this.titleInterestUrl) {
        this.interestsLoading = true;
        try {
          const result = await this.http({
            url: this.titleInterestUrl,
            dontShowError: true,
          });
          if (!result.error) {
            this.interests = result.response.data.interests;
          } else if (
            result.error.response.status === 404 &&
            !this.isMaxDateRange
          ) {
            // there is no interest for the selected time range
            // we try it without the time range
            const result = await this.http({
              url: this.titleInterestUrlNoDates,
              dontShowError: true,
            });
            if (!result.error) {
              this.hasInterestOutsideOfTimeRange = true;
            }
          }
        } finally {
          this.interestsLoading = false;
        }
      }
    },
    async loadPlatform() {
      if (this.selectedOrganization && this.platformId) {
        const result = await this.http({
          url: `/api/organization/${this.selectedOrganization.pk}/platform/${this.platformId}/`,
        });
        if (!result.error) {
          this.platformData = result.response.data;
        }
      }
    },
    async loadAllPlatforms() {
      if (this.selectedOrganization) {
        const result = await this.http({
          url: `/api/organization/${this.selectedOrganization.pk}/title/${this.titleId}/platforms/?start=${this.dateRangeStart}&end=${this.dateRangeEnd}`,
        });
        if (!result.error) {
          this.availableFromPlatforms = result.response.data;
        }
      }
    },
    annotationsLoaded({ count }) {
      this.annotationsCount = count;
    },
  },
  created() {
    if (this.platformId) {
      this.loadPlatform();
    }
    this.loadTitle();
    this.loadAllPlatforms();
  },
  watch: {
    selectedOrganizationId() {
      if (this.platformId) {
        this.loadPlatform();
      }
      this.loadTitle();
      this.loadAllPlatforms();
    },
    titleInterestUrl() {
      this.loadInterest();
      this.loadAllPlatforms();
    },
  },
};
</script>

<style scoped lang="scss"></style>
