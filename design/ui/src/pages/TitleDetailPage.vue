<i18n lang="yaml" src="@/locales/charts.yaml"></i18n>

<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<i18n lang="yaml">
en:
  export: Export
  available_from_platforms: Available from platforms
  this_title_on_platform: Link to this title on the selected platform
  this_title_no_platform: Link to all data for this title without platform filter
  current_platform: Current platform
  no_platform: Regardless of platform
  not_available_from_any_platform: This title did not appear on any platform in the selected time period.
  try_larger_window: Try selecting a broader date range.
cs:
  export: Export
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
          <tr v-if="title">
            <th>
              <v-tooltip max-width="600px" location="bottom">
                <template #activator="{ props }">
                  <span v-bind="props">
                    {{ $t("title_fields.proprietary_ids") }}
                    <v-icon color="info" size="small">fa fa-info-circle</v-icon>
                  </span>
                </template>
                <span v-text="$t('title_fields.proprietary_ids_tt')"></span>
              </v-tooltip>
            </th>
            <td>
              <ul
                class="no-bullets fixed-height"
                :class="title.proprietary_ids.length > 4 ? 'text-caption' : ''"
              >
                <li v-for="(pid, index) in title.proprietary_ids" :key="index">
                  {{ pid }}
                </li>
              </ul>
            </td>
          </tr>
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
                <v-icon size="x-small" color="warning" class="mb-1"
                  >fa fa-exclamation-triangle</v-icon
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
              <v-tooltip location="bottom" v-if="platform.pk !== platformId">
                <template v-slot:activator="{ props }">
                  <v-btn
                    size="small"
                    icon
                    variant="text"
                    v-bind="props"
                    color="secondary"
                    :to="{
                      name: 'platform-title-detail',
                      params: { platformId: platform.pk, titleId: titleId },
                    }"
                  >
                    <v-icon size="small">fas fa-external-link-alt</v-icon>
                  </v-btn>
                </template>
                <span v-text="$t('this_title_on_platform')"></span>
              </v-tooltip>
              <v-tooltip location="bottom" v-else>
                <template v-slot:activator="{ props }">
                  <span v-bind="props">
                    <v-btn
                      size="small"
                      variant="text"
                      icon
                      color="secondary"
                      disabled
                    >
                      <v-icon size="small">fas fa-arrow-left</v-icon>
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
              <v-tooltip location="bottom">
                <template v-slot:activator="{ props }">
                  <v-btn
                    size="small"
                    icon
                    variant="text"
                    v-bind="props"
                    color="secondary"
                    :to="{
                      name: 'title-detail',
                      params: { platformId: null, titleId: titleId },
                    }"
                  >
                    <v-icon size="small">fas fa-external-link-alt</v-icon>
                  </v-btn>
                </template>
                <span v-text="$t('this_title_no_platform')"></span>
              </v-tooltip>
            </td>
          </tr>
        </table>
      </v-col>
      <v-spacer></v-spacer>
      <v-col cols="14" sm="9" md="6" lg="3">
        <TagCard
          v-if="titleId"
          scope="title"
          :item-id="titleId"
          show-class
        ></TagCard>
      </v-col>
    </v-row>
    <section class="my-4" id="annotations">
      <AnnotationsWidget
        v-if="platformData"
        :platform="platformData"
        @loaded="annotationsLoaded"
      ></AnnotationsWidget>
    </section>
    <v-tabs
      v-if="isReady"
      v-model="tab"
      color="#2d5854"
      centered
      bg-color="rgb(45 88 84 / 5%)"
      grow
      class="mt-1"
    >
      <v-tab value="charts">{{ $t("charts") }}</v-tab>
      <v-tab value="items" v-if="enableItems">{{ $t("labels.items") }}</v-tab>
    </v-tabs>
    <v-tabs-window v-model="tab" class="platform-page">
      <v-tabs-window-item value="charts">
        <v-container>
          <v-row>
            <v-col>
              <h3>{{ $t("overview") }}</h3>
            </v-col>
            <v-col cols="auto">
              <raw-data-export-widget
                :title="titleId"
                :platform="platformId"
                :text="$t('export')"
                color="primary"
              >
              </raw-data-export-widget>
            </v-col>
          </v-row>
          <CounterChartSet
            :platform-id="platformId"
            :title-id="titleId"
            :report-views-url="reportViewsUrl"
            secondary-dimension-fallback="target"
            scope="title"
            show-reporting-link
          >
          </CounterChartSet>
        </v-container>
      </v-tabs-window-item>
      <v-tabs-window-item value="items" v-if="enableItems">
        <InterestGroupSelector class="px-4"></InterestGroupSelector>
        <ItemList
          :organization-id="selectedOrganization.pk"
          :platform-id="platformId"
          :title-id="titleId"
          :order-interest="orderInterest"
        ></ItemList>
      </v-tabs-window-item>
    </v-tabs-window>
  </v-container>
</template>

<script>
import { mapActions, mapGetters, mapState } from "vuex";
import CounterChartSet from "@/components/charts/CounterChartSet";
import AnnotationsWidget from "@/components/AnnotationsWidget";
import { useGoTo } from "vuetify";
import { formatInteger } from "@/libs/numbers";
import cancellation from "@/mixins/cancellation";
import TagCard from "@/components/tags/TagCard";
import RawDataExportWidget from "@/components/RawDataExportWidget";
import ItemList from "@/components/items/ItemList.vue";
import InterestGroupSelector from "@/components/selectors/InterestGroupSelector";

export default {
  name: "TitleDetailPage",
  components: {
    ItemList,
    TagCard,
    CounterChartSet,
    AnnotationsWidget,
    InterestGroupSelector,
    RawDataExportWidget,
  },
  mixins: [cancellation],
  props: {
    platformId: { required: false, type: Number },
    titleId: { required: true, type: Number },
  },

  setup() {
    const goTo = useGoTo();
    return { goTo };
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
      tab: "charts",
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
      enableItems: "enableItems",
    }),
    ...mapGetters("interest", {
      activeInterestGroups: "selectedGroupObjects",
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
    orderInterest() {
      // The interest that should be used for sorting the titles
      if (this.activeInterestGroups.length) {
        return this.activeInterestGroups[0].short_name;
      }
      return null;
    },
  },
  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
      changeDateSelectorHighlight: "changeDateSelectorHighlight",
    }),
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

<style scoped lang="scss">
ul.fixed-height {
  max-height: 6rem;
  overflow-y: auto;
}
</style>
