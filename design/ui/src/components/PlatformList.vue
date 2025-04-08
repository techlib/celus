<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<i18n lang="yaml">
en:
  columns:
    id: ID
    name: Name
    provider: Provider
    title_count: Title / database count
    sushi_available: SUSHI active
    notes: " "
    actions: Actions
  sushi_present: SUSHI is available and active for this platform
  no_sushi: SUSHI is not activated for this platform and selected organization
  sushi_for_version: "SUSHI for COUNTER version {version} is available"
  sushi_for_version_outside: "SUSHI not managed by consortium for COUNTER version {version} is available"
  annotations_available: |
    There are annotations for this platform and the current date range. Go to the
    platform page for details.

cs:
  columns:
    id: ID
    name: Název
    provider: Poskytovatel
    title_count: Počet titulů a databází
    sushi_available: Aktivní SUSHI
    notes: " "
    actions: Akce
  sushi_present: SUSHI je pro tuto platformu aktivní
  no_sushi: SUSHI není pro tuto platformu a vybranou organizaci aktivní
  sushi_for_version: "SUSHI pro verzi {version} COUNTERu je k dispozici"
  sushi_for_version_outside: "SUSHI nespravované konsorciem pro verzi {version} COUNTERu je k dispozici"
  annotations_available: |
    Pro tuto platformu a vybrané časové období byly uloženy poznámky.
    Na stránce platformy zjistíte detaily.
</i18n>

<template>
  <v-container fluid class="pt-0 px-0 px-sm-2">
    <v-row>
      <v-col class="pt-0">
        <TagSelector
          v-model="selectedTags"
          scope="platform"
          dont-check-exclusive
        ></TagSelector>
      </v-col>
      <v-spacer></v-spacer>
      <v-col class="pt-0">
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
      <v-col class="px-0 px-sm-2">
        <v-skeleton-loader v-if="loading" type="table"></v-skeleton-loader>
        <v-data-table
          v-else
          :items="visiblePlatforms"
          :headers="headers"
          :search="search"
          :page="page"
          :items-per-page="itemsPerPage"
          v-model:sort-by="orderBy"
          class="custom-header"
        >
          <template #item.name="{ item }">
            <router-link
              :to="{
                name: 'platform-detail',
                params: { platformId: item.pk },
              }"
              >{{ item.name || item.short_name }}
            </router-link>
          </template>
          <template #item.title_count="{ item }">
            <span
              v-if="item.title_count === 'loading'"
              class="fas fa-spinner fa-spin subdued"
            ></span>
            <span v-else>
              {{ formatInteger(item.title_count) }}
            </span>
          </template>
          <template #item.actions="{ item }">
            <v-btn
              v-if="showPlatformEditButton(item)"
              variant="text"
              size="small"
              color="secondary"
              @click.stop="
                selectedPlatform = item;
                showEditDialog = true;
              "
            >
              <v-icon left size="x-small" icon="fas fa-edit"></v-icon>
              {{ $t("actions.edit") }}
            </v-btn>
          </template>
          <template
            v-for="ig in activeInterestGroups"
            :key="ig.pk"
            v-slot:[slotName(ig)]="{ item }"
          >
            <span
              v-if="item.interests.loading"
              class="fas fa-spinner fa-spin subdued"
            >
            </span>
            <span v-else>
              {{ formatInteger(item.interests[ig.short_name]) }}
            </span>
          </template>
          <template #item.sushi_credentials_versions="{ item }">
            <v-tooltip
              location="bottom"
              v-for="record in item.sushi_credentials_versions"
              :key="10 * record.version + record.outside_consortium"
            >
              <template v-slot:activator="{ props }">
                <span v-bind="props" class="mr-3 subdued"
                  >{{ counterVersionToStr(record.version)
                  }}{{ record.outside_consortium ? "*" : "" }}</span
                >
              </template>
              <template v-if="record.outside_consortium">
                <i18n-t keypath="sushi_for_version_outside" tag="span">
                  <template v-slot:version>
                    {{ counterVersionToStr(record.version) }}
                  </template>
                </i18n-t>
              </template>
              <template v-else>
                <i18n-t keypath="sushi_for_version" tag="span">
                  <template v-slot:version>
                    {{ counterVersionToStr(record.version) }}
                  </template>
                </i18n-t>
              </template>
            </v-tooltip>
          </template>
          <template #item.annotations="{ item }">
            <v-tooltip location="bottom" v-if="item.annotations">
              <template v-slot:activator="{ props }">
                <v-icon
                  size="x-small"
                  v-bind="props"
                  icon="fa fa-exclamation-triangle"
                ></v-icon>
              </template>
              {{ $t("annotations_available") }}
            </v-tooltip>
          </template>
          <template #item.tags="{ item }">
            <TagChip
              v-for="tag in objIdToTags.get(item.pk)"
              :key="tag.pk"
              :tag="tag"
              small
              show-class
            ></TagChip>
          </template>

          <template #no-data v-if="!filtersApplied">
            <NoDataInTableWidget scope="platform" />
          </template>
        </v-data-table>
      </v-col>
    </v-row>
    <v-dialog v-model="showEditDialog" :max-width="dialogMaxWidth">
      <PlatformEditDialog
        :platform-id="selectedPlatform && selectedPlatform.pk"
        v-if="showEditDialog"
        @close="closeEditDialog"
        @saved="editDialogSaved"
      ></PlatformEditDialog>
    </v-dialog>
  </v-container>
</template>

<script>
import { mapGetters } from "vuex";
import { formatInteger } from "../libs/numbers";
import PlatformEditDialog from "@/components/PlatformEditDialog";
import cancellation from "@/mixins/cancellation";
import tags from "@/mixins/tags";
import TagChip from "@/components/tags/TagChip";
import TagSelector from "@/components/tags/TagSelector";
import { intersection } from "lodash";
import stateTracking from "@/mixins/stateTracking";
import NoDataInTableWidget from "@/components/NoDataInTableWidget.vue";
import { counterVersionToStr } from "@/libs/sushi";

export default {
  name: "PlatformList",

  components: {
    NoDataInTableWidget,
    TagSelector,
    TagChip,
    PlatformEditDialog,
  },

  mixins: [cancellation, tags, stateTracking],

  props: {
    dialogMaxWidth: {
      required: false,
      default: "1200px",
    },
    loading: Boolean,
    platforms: {},
  },

  data() {
    return {
      search: "",
      showEditDialog: false,
      selectedPlatform: null,
      resolvingTagsForIds: new Set(),
      // table options
      page: 1,
      itemsPerPage: -1,
      orderBy: [{ key: "name", order: this.orderDesc ? "desc" : "asc" }],
      orderDesc: false,
      // state tracking support
      watchedAttrs: [
        {
          name: "search",
          type: String,
        },
        {
          name: "page",
          type: Number,
        },
        {
          name: "itemsPerPage",
          type: Number,
          var: "ipp",
        },
        {
          name: "orderBy",
          type: Object,
        },
        {
          name: "orderDesc",
          type: Boolean,
        },
        {
          name: "selectedTags",
          type: Object,
        },
      ],
    };
  },

  computed: {
    ...mapGetters({
      formatNumber: "formatNumber",
      allowUserCreatePlatforms: "allowUserCreatePlatforms",
      showManagementStuff: "showManagementStuff",
    }),
    ...mapGetters("interest", {
      activeInterestGroups: "selectedGroupObjects",
    }),
    headers() {
      let base = [
        {
          title: this.$i18n.t("columns.name"),
          value: "name",
          key: "name",
        },
        {
          title: this.$t("columns.notes"),
          value: "annotations",
          sortable: false,
          key: "annotations",
        },
        {
          title: this.$i18n.t("columns.provider"),
          value: "provider",
          key: "provider",
        },
        {
          title: this.$i18n.t("labels.tags"),
          value: "tags",
        },
        {
          title: this.$i18n.t("columns.title_count"),
          value: "title_count",
          class: "wrap",
          align: "end",
          key: "title_count",
        },
      ];
      for (let ig of this.activeInterestGroups) {
        base.push({
          title: ig.name,
          value: "interests." + ig.short_name,
          class: "wrap text-xs-right",
          align: "end",
          key: "interests." + ig.short_name,
        });
      }
      base.push({
        title: this.$i18n.t("columns.sushi_available"),
        value: "sushi_credentials_versions",
        sortable: false,
      });
      if (this.allowUserCreatePlatforms) {
        base.push({
          title: this.$i18n.t("columns.actions"),
          value: "actions",
          sortable: false,
        });
      }
      // if (this.enableTags) {
      //   base.splice(3, 0, {
      //     title: this.$i18n.t("labels.tags"),
      //     value: "tags",
      //     key: "tags",
      //   });
      // }
      return base;
    },
    filtersApplied() {
      // boolean, whether any filters are applied
      return this.selectedTags.length > 0 || this.search;
    },
    visiblePlatforms() {
      // filter platforms by tag
      if (this.selectedTags.length > 0) {
        return this.platforms.filter((pl) => {
          if (this.objIdToTags.has(pl.pk)) {
            const tags = this.objIdToTags.get(pl.pk).map((tag) => tag.pk);
            if (intersection(tags, this.selectedTags).length) {
              return true;
            }
          }
          return false;
        });
      }
      return this.platforms;
    },
  },

  methods: {
    counterVersionToStr(value) {
      return counterVersionToStr(value);
    },
    editDialogSaved(platform) {
      this.showEditDialog = false;
      this.$emit("update-platforms", platform);
    },
    closeEditDialog() {
      this.showEditDialog = false;
    },
    formatInteger: formatInteger,
    slotName(ig) {
      return "item.interests." + ig.short_name;
    },
    async syncTags() {
      let toTag = this.platforms
        .map((pl) => pl.pk)
        .filter((pk) => !this.objIdToTags.has(pk));
      if (this.resolvingTagsForIds.size) {
        // we only want to resolve those that are not already being resolved
        toTag = toTag.filter((pk) => !this.resolvingTagsForIds.has(pk));
      }
      // we extend the set of what is being resolved
      toTag.forEach((pk) => this.resolvingTagsForIds.add(pk));

      if (toTag.length) {
        try {
          await this.getTagsForObjectsById("platform", toTag);
        } finally {
          // clean up the set of what was resolved
          toTag.forEach((pk) => this.resolvingTagsForIds.delete(pk));
        }
      }
    },
    showPlatformEditButton(platform) {
      return platform.source?.organization || this.showManagementStuff;
    },
  },

  created() {
    // when switching between different "tabs" on the platforms page
    // this widget may get created without the platforms being loaded
    // because they are present from the previous load
    // in that case the watcher for platforms will not be triggered
    // and we need to make sure tags are loaded
    this.syncTags();
  },

  watch: {
    showEditDialog(value) {
      if (!value) {
        this.selectedPlatform = null;
      }
    },
    async platforms() {
      if (this.platforms.length) {
        await this.syncTags();
      }
    },
  },
};
</script>

<style lang="scss" scoped>
:deep(.v-table > .v-table__wrapper > table > thead > tr > th) {
  font-size: 12px;
}
</style>
