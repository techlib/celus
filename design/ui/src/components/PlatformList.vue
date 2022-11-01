<i18n lang="yaml" src="../locales/common.yaml"></i18n>

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
  annotations_available:
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
  annotations_available:
    Pro tuto platformu a vybrané časové období byly uloženy poznámky.
    Na stránce platformy zjistíte detaily.
</i18n>
<template>
  <v-container fluid class="pt-0 px-0 px-sm-2">
    <v-row>
      <v-col v-if="enableTags" class="pt-0">
        <TagSelector
          v-model="selectedTags"
          scope="platform"
          dont-check-exclusive
        />
      </v-col>
      <v-spacer></v-spacer>
      <v-col class="pt-0">
        <v-text-field
          v-model="search"
          append-icon="fa-search"
          :label="$t('labels.search')"
          single-line
          hide-details
        ></v-text-field>
      </v-col>
    </v-row>
    <v-row>
      <v-col class="px-0 px-sm-2">
        <v-data-table
          :items="visiblePlatforms"
          :headers="headers"
          :items-per-page="-1"
          :search="search"
          sort-by="name"
          :loading="loading"
        >
          <template v-slot:item.name="{ item }">
            <router-link
              :to="{
                name: 'platform-detail',
                params: { platformId: item.pk },
              }"
              >{{ item.name || item.short_name }}
            </router-link>
          </template>
          <template v-slot:item.title_count="{ item }">
            <span
              v-if="item.title_count === 'loading'"
              class="fas fa-spinner fa-spin subdued"
            ></span>
            <span v-else>
              {{ formatInteger(item.title_count) }}
            </span>
          </template>
          <template v-slot:item.actions="{ item }">
            <v-btn
              v-if="item.source && item.source.organization"
              text
              small
              color="secondary"
              @click.stop="
                selectedPlatform = item;
                showEditDialog = true;
              "
            >
              <v-icon left x-small>fa-edit</v-icon>
              {{ $t("actions.edit") }}
            </v-btn>
          </template>
          <template
            v-for="ig in activeInterestGroups"
            v-slot:[slotName(ig)]="{ item }"
          >
            <span
              v-if="item.interests.loading"
              class="fas fa-spinner fa-spin subdued"
              :key="ig.pk"
            ></span>
            <span v-else :key="ig.pk">
              {{ formatInteger(item.interests[ig.short_name]) }}
            </span>
          </template>
          <template v-slot:item.sushi_credentials_versions="{ item }">
            <v-tooltip
              bottom
              v-for="record in item.sushi_credentials_versions"
              :key="10 * record.version + record.outside_consortium"
            >
              <template v-slot:activator="{ on }">
                <span v-on="on" class="mr-3 subdued"
                  >{{ record.version
                  }}{{ record.outside_consortium ? "*" : "" }}</span
                >
              </template>
              <template v-if="record.outside_consortium">
                <i18n path="sushi_for_version_outside" tag="span">
                  <template v-slot:version>
                    {{ record.version }}
                  </template>
                </i18n>
              </template>
              <template v-else>
                <i18n path="sushi_for_version" tag="span">
                  <template v-slot:version>
                    {{ record.version }}
                  </template>
                </i18n>
              </template>
            </v-tooltip>
          </template>
          <template v-slot:item.annotations="{ item }">
            <v-tooltip bottom v-if="item.annotations">
              <template v-slot:activator="{ on }">
                <v-icon x-small v-on="on">fa-exclamation-triangle</v-icon>
              </template>
              <template>
                {{ $t("annotations_available") }}
              </template>
            </v-tooltip>
          </template>

          <template #item.tags="{ item }">
            <TagChip
              v-for="tag in objIdToTags.get(item.pk)"
              :key="tag.pk"
              :tag="tag"
              small
              show-class
            />
          </template>
        </v-data-table>
      </v-col>
    </v-row>
    <v-dialog v-model="showEditDialog" :max-width="dialogMaxWidth">
      <PlatformEditDialog
        ref="widget"
        :platform-id="selectedPlatform && selectedPlatform.pk"
        v-if="showEditDialog"
        @close="closeEditDialog()"
        @saved="editDialogSaved"
        key="edit"
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

export default {
  name: "PlatformList",

  components: {
    TagSelector,
    TagChip,
    PlatformEditDialog,
  },

  mixins: [cancellation, tags],

  props: {
    dialogMaxWidth: {
      required: false,
      default: "1200px",
    },
    loading: {},
    platforms: {},
  },

  data() {
    return {
      search: "",
      showEditDialog: false,
      selectedPlatform: null,
    };
  },

  computed: {
    ...mapGetters({
      formatNumber: "formatNumber",
      allowUserCreatePlatforms: "allowUserCreatePlatforms",
      enableTags: "enableTags",
    }),
    ...mapGetters("interest", {
      activeInterestGroups: "selectedGroupObjects",
    }),
    headers() {
      let base = [
        {
          text: this.$i18n.t("columns.name"),
          value: "name",
        },
        {
          text: this.$t("columns.notes"),
          value: "annotations",
          sortable: false,
        },
        {
          text: this.$i18n.t("columns.provider"),
          value: "provider",
        },
        {
          text: this.$i18n.t("columns.title_count"),
          value: "title_count",
          class: "wrap",
          align: "right",
        },
      ];
      for (let ig of this.activeInterestGroups) {
        base.push({
          text: ig.name,
          value: "interests." + ig.short_name,
          class: "wrap text-xs-right",
          align: "right",
        });
      }
      base.push({
        text: this.$i18n.t("columns.sushi_available"),
        value: "sushi_credentials_versions",
        sortable: false,
      });
      if (this.allowUserCreatePlatforms) {
        base.push({
          text: this.$i18n.t("columns.actions"),
          value: "actions",
          sortable: false,
        });
      }
      if (this.enableTags) {
        base.splice(3, 0, {
          text: this.$i18n.t("labels.tags"),
          value: "tags",
        });
      }
      return base;
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
    editDialogSaved(platform) {
      console.log(platform);
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
  },

  watch: {
    showEditDialog(value) {
      if (!value) {
        this.selectedPlatform = null;
      }
    },
    platforms() {
      if (this.platforms.length) {
        this.getTagsForObjectsById(
          "platform",
          this.platforms.map((item) => item.pk)
        );
      }
    },
  },
};
</script>
