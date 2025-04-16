<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml" src="@/locales/counter_registry.yaml"></i18n>

<template>
  <v-container fluid class="pt-0 px-0 px-sm-2">
    <v-row>
      <v-col>
        <p class="font-italic">
          {{ $t("counter_registry.platform_differences") }}
        </p>
      </v-col>
    </v-row>
    <v-row>
      <v-col class="pt-6">
        <v-btn
          color="primary"
          :disabled="loading || updating || !selectedCounterPlatforms.length"
          @click="triggerUpdate"
        >
          {{ $t("counter_registry.trigger_update") }} ({{
            selectedCounterPlatforms.length
          }})
        </v-btn>
      </v-col>
      <v-col>
        <v-select
          v-model="filter"
          :items="filters"
          :label="$t('counter_registry.filter')"
          item-title="text"
        >
        </v-select>
      </v-col>
      <v-col>
        <v-text-field
          v-model="search"
          append-inner-icon="fa fa-search"
          :label="$t('labels.search')"
          single-line
          hide-details
        >
        </v-text-field>
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="auto">
        <v-chip
          :prepend-icon="icons.different"
          color="error"
          @click="filter = 'different'"
        >
          {{ $t("counter_registry.filters.different") }}
          <strong class="ml-2">
            {{ updatableCount }}
          </strong>
        </v-chip>
      </v-col>
      <v-col cols="auto">
        <v-chip
          :prepend-icon="icons.missing"
          color="success"
          @click="filter = 'missing'"
        >
          {{ $t("counter_registry.filters.missing") }}
          <strong class="ml-2">
            {{ missingCount }}
          </strong>
        </v-chip>
      </v-col>
      <v-col cols="auto">
        <v-chip
          :prepend-icon="icons.same"
          color="info"
          @click="filter = 'same'"
        >
          {{ $t("counter_registry.filters.same") }}
          <strong class="ml-2">
            {{ sameCount }}
          </strong>
        </v-chip>
      </v-col>
    </v-row>
    <v-row>
      <v-col class="px-0 px-sm-2">
        <v-data-table
          :item-selectable="selectablePlatform"
          v-model="selectedCounterPlatforms"
          :items="counterPlatformsToShow"
          :headers="headers"
          :search="search"
          :page="page"
          :items-per-page="itemsPerPage"
          v-model:sort-by="orderBy"
          show-select
          item-value="id"
          item-key="id"
          multi-sort
          show-expand
          :loading="loading"
          :cell-props="cellProps"
        >
          <template v-slot:loading>
            <v-skeleton-loader type="table-row@20"></v-skeleton-loader>
          </template>

          <template #item.name="{ item }">
            <v-icon
              v-if="item.related_platform && item.keep_name"
              color="info"
              size="x-small"
              >{{ icons.same }}
            </v-icon>
            <v-icon
              v-else-if="item.related_platform && !item.keep_name"
              color="error"
              size="x-small"
              >{{ icons.different }}
            </v-icon>
            <v-icon color="success" size="x-small" v-else>
              {{ icons.missing }}
            </v-icon>
            <router-link
              v-if="item.related_platform"
              :to="{
                name: 'platform-detail',
                params: { platformId: item.related_platform },
              }"
              ><span class="ml-2">{{ item.name }}</span>
            </router-link>
            <span class="ml-2" v-else>{{ item.name }}</span>
          </template>

          <template #item.short_name="{ item }">
            <v-icon
              v-if="item.related_platform && item.keep_short_name"
              color="info"
              size="x-small"
              >{{ icons.same }}
            </v-icon>
            <v-icon
              v-else-if="item.related_platform && !item.keep_short_name"
              color="error"
              size="x-small"
              >{{ icons.different }}
            </v-icon>
            <v-icon color="success" size="x-small" v-else>
              {{ icons.missing }}
            </v-icon>
            <span
              :class="!!item.short_name ? '' : 'font-weight-bold'"
              class="ml-2"
              >{{ item.short_name || item.related_platform_short_name }}</span
            >
          </template>

          <template #item.provider="{ item }">
            <v-icon
              v-if="item.related_platform && item.keep_provider"
              color="info"
              size="x-small"
              >{{ icons.same }}
            </v-icon>
            <v-icon
              v-else-if="item.related_platform && !item.keep_provider"
              color="error"
              size="x-small"
              >{{ icons.different }}
            </v-icon>
            <v-icon color="success" size="x-small" v-else>
              {{ icons.missing }}
            </v-icon>
            <span
              :class="!!item.provider ? '' : 'font-weight-bold'"
              class="ml-2"
              >{{ item.provider || item.related_platform_provider }}</span
            >
          </template>

          <template #item.url="{ item }">
            <v-icon
              v-if="item.related_platform && item.keep_url"
              color="info"
              size="x-small"
              >{{ icons.same }}
            </v-icon>
            <v-icon
              v-else-if="item.related_platform && !item.keep_url"
              color="error"
              size="x-small"
              >{{ icons.different }}
            </v-icon>
            <v-icon color="success" size="x-small" v-else>
              {{ icons.missing }}
            </v-icon>
            <span :class="!!item.url ? '' : 'font-weight-bold'" class="ml-2">{{
              item.url || item.related_platform_url
            }}</span>
          </template>

          <template #item.sushi_services="{ item }">
            <v-icon
              v-if="item.related_platform && item.keep_knowledgebase"
              color="info"
              size="x-small"
              >{{ icons.same }}
            </v-icon>
            <v-icon
              v-else-if="item.related_platform && !item.keep_knowledgebase"
              color="error"
              size="x-small"
              >{{ icons.different }}
            </v-icon>
            <v-icon color="success" size="x-small" v-else>
              {{ icons.missing }}
            </v-icon>
          </template>

          <template #no-data>
            {{ $t("counter_registry.no_data") }}
          </template>
          <template v-slot:expanded-row="{ columns, item }">
            <tr>
              <td :colspan="columns.length" class="pb-3">
                <CounterRegistryDiffWidget
                  :platform-diff="item"
                  :checked="selectedCounterPlatforms.includes(item.id)"
                >
                </CounterRegistryDiffWidget>
              </td>
            </tr>
          </template>

          <template #item.notes="{ item }">
            <v-tooltip location="left">
              <template #activator="{ props }">
                <v-icon
                  v-bind="props"
                  v-if="item.notes"
                  color="info"
                  icon="fa fa-comment"
                  size="small"
                  >fa fa-comment</v-icon
                >
              </template>
              <pre>{{ item.notes }}</pre>
            </v-tooltip>
          </template>
        </v-data-table>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import cancellation from "@/mixins/cancellation";
import CounterRegistryDiffWidget from "./CounterRegistryDiffWidget.vue";

export default {
  name: "CounterRegistryPlatformListWidget",

  components: {
    CounterRegistryDiffWidget,
  },

  mixins: [cancellation],

  props: {},

  data() {
    return {
      search: "",
      // table options
      page: 1,
      itemsPerPage: 20,
      orderBy: [],
      counterPlatforms: [],
      loading: false,
      updating: false,
      selectedCounterPlatforms: [],
      filter: "all",
      filters: [
        { text: this.$t("counter_registry.filters.all"), value: "all" },
        {
          text: this.$t("counter_registry.filters.different"),
          value: "different",
        },
        { text: this.$t("counter_registry.filters.missing"), value: "missing" },
        { text: this.$t("counter_registry.filters.same"), value: "same" },
      ],
      icons: {
        different: "fa fa-retweet",
        missing: "fa fa-plus",
        same: "fa fa-check",
      },
    };
  },

  computed: {
    headers() {
      return [
        {
          title: this.$i18n.t("counter_registry.columns.name"),
          value: "name",
          key: "name",
        },
        {
          title: this.$t("counter_registry.columns.short_name"),
          value: "short_name",
          key: "short_name",
        },
        {
          title: this.$i18n.t("counter_registry.columns.provider"),
          value: "provider",
          key: "provider",
        },
        {
          title: this.$i18n.t("counter_registry.columns.url"),
          value: "url",
          key: "url",
        },
        {
          title: this.$i18n.t("counter_registry.columns.sushi_services"),
          sortable: false,
          key: "sushi_services",
        },
        {
          title: this.$i18n.t("counter_registry.columns.notes"),
          sortable: true,
          key: "notes",
        },
      ];
    },
    applyData() {
      return {
        updates: this.selectedCounterPlatforms.map((e) => {
          return {
            id: e,
            name: true,
            short_name: true,
            provider: true,
            url: true,
            sushi_services: true,
          };
        }),
      };
    },
    counterPlatformsToShow() {
      if (this.filter === "different") {
        return this.counterPlatforms.filter((e) => this.updatablePlatform(e));
      }
      if (this.filter === "missing") {
        return this.counterPlatforms.filter((e) => this.missingPlatform(e));
      }
      if (this.filter === "same") {
        return this.counterPlatforms.filter(
          (e) => !this.updatablePlatform(e) && !this.missingPlatform(e),
        );
      }
      return this.counterPlatforms;
    },
    updatableCount() {
      return this.counterPlatforms.filter((e) => this.updatablePlatform(e))
        .length;
    },
    missingCount() {
      return this.counterPlatforms.filter((e) => this.missingPlatform(e))
        .length;
    },
    sameCount() {
      return this.counterPlatforms.filter(
        (e) => !this.updatablePlatform(e) && !this.missingPlatform(e),
      ).length;
    },
  },

  methods: {
    updatablePlatform(platformDiff) {
      // existing but different
      return (
        !(
          platformDiff.keep_knowledgebase &&
          platformDiff.keep_name &&
          platformDiff.keep_short_name &&
          platformDiff.keep_url &&
          platformDiff.keep_provider
        ) && platformDiff.related_platform
      );
    },
    missingPlatform(platformDiff) {
      // new platform - not in Celus yet
      return !platformDiff.related_platform;
    },
    selectablePlatform(platformDiff) {
      return (
        this.updatablePlatform(platformDiff) ||
        this.missingPlatform(platformDiff)
      );
    },
    async fetchCounterPlatforms() {
      this.loading = true;
      let result = await this.http({
        url: "/api/counter_registry/platforms_diff/",
        group: "platform-diff",
      });
      if (!result.error) {
        this.counterPlatforms = result.response.data;
      }
      if (result.error !== "canceled") {
        // if the request was cancelled, it means another request was made
        // so we do not want to switch loading off
        this.loading = false;
      }
    },
    async triggerUpdate() {
      this.updating = true;
      let result = await this.http({
        method: "post",
        url: "/api/counter_registry/platforms_diff/apply/",
        group: "platform-diff-update",
        data: this.applyData,
      });
      if (!result.error) {
        this.selectedCounterPlatforms = [];
        this.fetchCounterPlatforms();
      }
      this.updating = false;
    },
    cellProps({ item }) {
      if (this.updatablePlatform(item)) {
        return {
          class: { "bg-red-lighten-5": true },
        };
      }
      if (this.missingPlatform(item)) {
        return {
          class: { "bg-green-lighten-5": true },
        };
      }
      return {};
    },
  },

  mounted() {
    this.fetchCounterPlatforms();
  },
};
</script>

<style lang="scss" scoped>
// Darker tooltips
::v-deep(.v-overlay__content) {
  background-color: rgba(0, 0, 0, 0.8);
}
</style>
