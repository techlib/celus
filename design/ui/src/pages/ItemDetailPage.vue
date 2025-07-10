<i18n lang="yaml" src="@/locales/charts.yaml"></i18n>

<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

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
              <ShortenText :text="props.item.text"></ShortenText>
            </span>
          </template>
        </v-breadcrumbs>
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="auto">
        <table class="overview-card elevation-2">
          <tr v-if="this.platformId">
            <th>{{ $t("platform") }}</th>
            <td>{{ platformName }}</td>
          </tr>
          <tr v-if="this.titleId">
            <th>{{ $t("title") }}</th>
            <td>{{ titleName }}</td>
          </tr>
          <tr>
            <th>{{ $t("labels.item") }}</th>
            <td class="font-weight-medium">{{ itemName }}</td>
          </tr>
          <tr v-if="item">
            <th>{{ $t("labels.authors") }}</th>
            <td>
              <ul class="no-bullets fixed-height">
                <span
                  v-for="(author, index) in item.authors"
                  :key="index"
                  class="font-italic"
                  >{{ index > 0 ? ", " : "" }}{{ author.name }}</span
                >
              </ul>
            </td>
          </tr>
          <tr v-if="item">
            <th>{{ $t("title_fields.doi") }}</th>
            <td>
              <DoiLink :doi="item.doi"></DoiLink>
            </td>
          </tr>
          <template v-if="title">
            <tr v-for="(prop, index) in ['isbn', 'issn', 'eissn']" :key="index">
              <th>{{ $t("title_fields." + prop) }}</th>
              <td>{{ title[prop] }}</td>
            </tr>
          </template>
          <template v-else-if="item">
            <tr v-for="(prop, index) in ['isbn', 'issn', 'eissn']" :key="index">
              <th>{{ $t("title_fields." + prop) }}</th>
              <td>
                <router-link
                  :to="{
                    name: 'title-list',
                    query: {
                      search: item[prop],
                    },
                  }"
                  >{{ item[prop] }}</router-link
                >
              </td>
            </tr>
          </template>
          <tr v-if="item">
            <th>{{ $t("labels.publication_date") }}</th>
            <td>{{ item.publication_date ?? "" }}</td>
          </tr>
          <tr v-if="item">
            <th>
              <v-tooltip max-width="600px" location="bottom">
                <template #activator="{ props }">
                  <span v-bind="props">
                    {{ $t("title_fields.proprietary_ids") }}
                    <v-icon color="info" size="small">fa-info-circle</v-icon>
                  </span>
                </template>
                <span v-text="$t('title_fields.proprietary_ids_tt')"></span>
              </v-tooltip>
            </th>
            <td>
              <ul
                class="no-bullets fixed-height"
                :class="item.proprietary_ids.length > 4 ? 'text-caption' : ''"
              >
                <li v-for="(pid, index) in item.proprietary_ids" :key="index">
                  {{ pid }}
                </li>
              </ul>
            </td>
          </tr>
        </table>
      </v-col>
      <v-col cols="auto" v-if="item">
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
      <v-col cols="auto" v-if="item && item.parent_titles.length > 0">
        <table class="overview-card elevation-2">
          <tr class="header">
            <th
              colspan="2"
              v-text="$tc('labels.parent_title', item.parent_titles.length)"
            ></th>
          </tr>
          <tr v-for="t in item.parent_titles" :key="t.pk">
            <td>
              <router-link
                :to="{ name: 'title-detail', params: { titleId: t.pk } }"
                >{{ t.name }}</router-link
              >
            </td>
          </tr>
        </table>
      </v-col>
    </v-row>
    <section>
      <v-container fluid>
        <v-row>
          <v-col>
            <h3>{{ $t("overview") }}</h3>
          </v-col>
        </v-row>
        <v-row>
          <v-col>
            <CounterChartSet
              :platform-id="platformId"
              :title-id="titleId"
              :item-id="itemId"
              :report-views-url="reportViewsUrl"
              scope="title"
            >
            </CounterChartSet>
          </v-col>
        </v-row>
      </v-container>
    </section>
  </v-container>
</template>

<script>
import { mapActions, mapGetters, mapState } from "vuex";
import CounterChartSet from "@/components/charts/CounterChartSet";
import { formatInteger } from "@/libs/numbers";
import cancellation from "@/mixins/cancellation";
import DoiLink from "@/components/util/DoiLink.vue";
import ShortenText from "@/components/ShortenText.vue";

export default {
  name: "TitleDetailPage",
  components: {
    ShortenText,
    DoiLink,
    CounterChartSet,
  },
  mixins: [cancellation],
  props: {
    platformId: { required: false, type: Number },
    titleId: { required: false, type: Number },
    itemId: { required: true, type: Number },
  },
  data() {
    return {
      item: null,
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
    itemName() {
      if (this.item) {
        return this.item.name;
      }
      return "";
    },
    breadcrumbs() {
      if (this.platformId && this.titleId) {
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
            linkName: "platform-title-detail",
            linkParams: {
              platformId: this.platformId,
              titleId: this.titleId,
            },
          },
          {
            text: this.itemName,
          },
        ];
      } else if (this.platformId) {
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
            text: this.itemName,
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
          linkName: "title-detail",
          linkParams: {
            titleId: this.titleId,
          },
        },
        {
          text: this.itemName,
        },
      ];
    },
    itemInterestUrl() {
      if (this.itemInterestUrlNoDates) {
        return `${this.itemInterestUrlNoDates}?start=${this.dateRangeStart}&end=${this.dateRangeEnd}&interest=true&parent_titles=true`;
      }
      return null;
    },
    itemInterestUrlNoDates() {
      if (this.selectedOrganization && this.titleId && this.itemId) {
        if (this.platformId) {
          return `/api/organization/${this.selectedOrganization.pk}/platform/${this.platformId}/title/${this.titleId}/item/${this.itemId}/`;
        } else {
          // this is the case when no platform is specified
          return `/api/organization/${this.selectedOrganization.pk}/title/${this.titleId}/item/${this.itemId}/`;
        }
      } else if (this.selectedOrganization && this.itemId) {
        if (this.platformId) {
          return `/api/organization/${this.selectedOrganization.pk}/platform/${this.platformId}/item/${this.itemId}/`;
        } else {
          return `/api/organization/${this.selectedOrganization.pk}/item/${this.itemId}/`;
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
      if (this.itemInterestUrlNoDates) {
        return `${this.itemInterestUrlNoDates}report-views/`;
      }
      return null;
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
    formatInteger: formatInteger,
    async loadTitle() {
      if (this.titleUrl) {
        const result = await this.http({ url: this.titleUrl });
        if (!result.error) {
          this.title = result.response.data;
        }
      }
    },
    async loadInterest() {
      if (this.itemInterestUrl) {
        this.interestsLoading = true;
        try {
          const result = await this.http({
            url: this.itemInterestUrl,
            dontShowError: true,
          });
          if (!result.error) {
            this.interests = result.response.data.interests;
            this.item = result.response.data;
          } else {
            this.interests = {};
            this.item = null;
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
  },
  created() {
    if (this.platformId) {
      this.loadPlatform();
    }
    this.loadTitle();
    this.loadInterest();
  },
  watch: {
    selectedOrganizationId() {
      if (this.platformId) {
        this.loadPlatform();
      }
      this.loadTitle();
      this.loadInterest();
    },
    itemInterestUrl() {
      this.loadInterest();
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
