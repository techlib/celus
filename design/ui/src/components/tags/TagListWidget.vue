<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<i18n lang="yaml">
en:
  confirm_tag_delete: Confirm tag delete
  delete_tag_item_count: Do you want to delete tag "{tag}" used by {count} item? | Do you wan't to delete tag "{tag}" used by {count} items?
  tag_delete_success: Tag "{tag}" was successfully deleted
  confirm_tag_class_delete: Confirm tag class delete
  delete_tag_class_tag_count: Do you want to delete tag class "{name}" with {count} tag? | Do you want to delete tag class "{name}" with {count} tags?
  tag_class_delete_success: Tag class "{tag_class}" was successfully deleted
  performance_warning: In order to optimize performance when many tags are shown, only the text of the tags is shown, not a full preview.
  show_system_tags: Show system tags
  tag_class_hidden: Tags from this class will not be shown when listing tagged items, such as titles. Click to toggle.
  tag_class_visible: Tags from this class will be shown when listing tagged items, such as titles. Click to toggle.

cs:
  confirm_tag_delete: Potvrzení smazání štítku
  delete_tag_item_count: Opravdu chcete smazat štítek "{tag}" použitý u {count} položky? | Opravdu chcete smazat štítek "{tag}" použitý u {count} položek?
  tag_delete_success: Štítek "{tag}" byl úspěšně smazán
  confirm_tag_class_delete: Potvrzení smazání typu štítků
  delete_tag_class_tag_count: Opravdu chcete smazat typ štítků "{name}" s {count} štítkem? | Opravdu chcete smazat typ štítků "{name}" s {count} štítky?
  tag_class_delete_success: Typ štítků "{tag_class}" byl úspěšně smazán
  performance_warning: Pro optimalizaci výkonu, když je zobrazeno mnoho štítků, je zobrazen pouze text štítku, nikoliv plný náhled.
  show_system_tags: Zobrazit systémové štítky
  tag_class_hidden: Tento typ štítků nebude zobrazen při výpisu položek se štítky, například titulů. Kliknutím přepnete.
  tag_class_visible: Tento typ štítků bude zobrazen při výpisu položek se štítky, například titulů. Kliknutím přepnete.
</i18n>

<template>
  <div>
    <v-skeleton-loader v-if="loading" type="table"></v-skeleton-loader>
    <v-data-table
      v-else
      :items="visibleTags"
      :headers="headers"
      density="comfortable"
      item-key="pk"
      item-value="name"
      v-model:items-per-page="itemsPerPage"
      v-model:page="page"
      v-model:sort-by="orderBy"
      hide-default-footer
      :search="search"
      :group-by="[{ key: groupByClass ? '_group_sorter' : null }]"
      :custom-group="groupingFn"
    >
      <template #top>
        <v-row v-if="optimizePerformance">
          <v-col cols="12" class="pb-0">
            <v-alert type="info" density="compact" text>
              {{ $t("performance_warning") }}
            </v-alert>
          </v-col>
        </v-row>
        <v-row class="d-flex align-center">
          <v-col class="align-self-center" cols="auto">
            <AddTagClassButton
              color="defaultButton"
              @saved="fetchTagClasses()"
            ></AddTagClassButton>
          </v-col>
          <v-col class="align-self-center" cols="auto">
            <AddTagButton
              @saved="fetchTags()"
              flat
              color="primary"
            ></AddTagButton>
          </v-col>
          <v-spacer></v-spacer>
          <v-col cols="auto" class="mt-4">
            <v-switch
              v-model="showSystemTags"
              :label="$t('show_system_tags')"
              color="primary"
              density="comfortable"
            ></v-switch>
          </v-col>
          <v-col cols="2">
            <v-select
              :items="tagScopes"
              v-model="tagScope"
              density="comfortable"
              :label="$t('labels.tag_scope')"
            ></v-select>
          </v-col>
          <v-col class="mt-4" cols="auto" v-if="!optimizePerformance">
            <v-switch
              color="primary"
              v-model="showClass"
              density="comfortable"
              :label="$t('labels.show_class')"
            ></v-switch>
          </v-col>
          <!-- the following switch is probably not very useful, let's turn off -->
          <!--v-col cols="auto">
            <v-switch
              v-model="groupByClass"
              :label="$t('labels.group_by_class')"
            />
          </v-col-->
          <v-col>
            <v-text-field
              v-model="search"
              clearable
              density="comfortable"
              :label="$t('labels.search')"
            ></v-text-field>
          </v-col>
        </v-row>
      </template>
      <template #[`item.name`]="{ item }" v-if="optimizePerformance">
        <span class="fa fa-tag pe-1" :style="{ color: item.bg_color }"></span>
        {{ item.name }}
      </template>
      <template v-slot:[`item.name`]="{ item }" v-else>
        <TagChip :tag="item" :show-class="showClass" link></TagChip>
      </template>
      <template #[`item._group_sorter`]="{ item }" v-if="optimizePerformance">
        {{ item.tag_class.name }}
        <span class="text-caption text-secondary"
          >[{{ $t(item.tag_class.scope) }}]</span
        >
      </template>
      <template #[`item._group_sorter`]="{ item }" v-else>
        <TagClassScopeWidget
          :scope="item.tag_class.scope"
          class="pl-3 text-caption text-disabled"
        ></TagClassScopeWidget>
      </template>
      <template #[`item.can_see`]="{ item }">
        <span class="text-caption">{{
          tagAccessLevelToText[item.can_see]
        }}</span>
      </template>
      <template #[`item.can_assign`]="{ item }">
        <span class="text-caption">{{
          tagAccessLevelToText[item.can_assign]
        }}</span>
      </template>
      <template #[`item.actions`]="{ item }">
        <v-btn
          @click="editTag(item)"
          size="small"
          icon
          density="comfortable"
          variant="text"
          v-if="item.user_can_modify"
          color="lighterIcons"
        >
          <v-icon size="small">fa fa-edit</v-icon>
        </v-btn>
        <v-btn
          @click="deleteTag(item)"
          size="small"
          density="comfortable"
          icon
          color="lighterIcons"
          variant="text"
          v-if="item.user_can_modify"
        >
          <v-icon size="small">fa fa-trash</v-icon>
        </v-btn>
      </template>
      <template
        v-slot:[`group-header`]="{ item, isGroupOpen, toggleGroup, columns }"
      >
        <tr class="group_header">
          <td class="group_column">
            <v-btn
              @click="toggleGroup(item)"
              size="x-small"
              variant="text"
              icon
            >
              <v-icon size="x-small">{{
                isGroupOpen(item) ? "fa fa-minus" : "fa fa-plus"
              }}</v-icon>
            </v-btn>
          </td>
          <td class="tag_column">
            <span class="font-weight-light pr-2"
              >{{ $t("labels.tag_class") }}:</span
            >
            <span
              class="font-weight-bold"
              v-if="classIdToObj.has(item.items[0].raw.tag_class.pk)"
              >{{ classIdToObj.get(item.items[0].raw.tag_class.pk).name }}</span
            >
          </td>
          <td :colspan="columns.length - 3">
            <span class="font-weight-light pr-2"
              >{{ $t("labels.tag_scope") }}:</span
            >
            <span
              class="font-weight-bold"
              v-if="classIdToObj.has(item.items[0].raw.tag_class.pk)"
            >
              <TagClassScopeWidget
                :scope="classIdToObj.get(item.items[0].raw.tag_class.pk).scope"
                icon-color="#a0a0a0"
                style="color: rgba(0, 0, 0, 0.6)"
              ></TagClassScopeWidget>
            </span>
          </td>
          <td>
            <v-btn
              v-if="
                classIdToObj.has(item.items[0].raw.tag_class.pk) &&
                classIdToObj.get(item.items[0].raw.tag_class.pk).user_can_modify
              "
              size="small"
              density="comfortable"
              icon
              color="lighterIcons"
              variant="text"
              @click="editClass(item.items[0].raw.tag_class.pk)"
            >
              <v-icon size="small">fas fa-edit</v-icon>
            </v-btn>
            <v-btn
              v-if="
                classIdToObj.has(item.items[0].raw.tag_class.pk) &&
                classIdToObj.get(item.items[0].raw.tag_class.pk).user_can_modify
              "
              size="small"
              density="comfortable"
              color="lighterIcons"
              icon
              variant="text"
              @click="deleteClass(item.items[0].raw.tag_class.pk)"
            >
              <v-icon size="small">fa fa-trash</v-icon>
            </v-btn>
            <v-tooltip
              location="bottom"
              max-width="600px"
              :key="'group-' + item.items[0].raw.tag_class.pk"
            >
              <template #activator="{ props }">
                <v-btn
                  size="small"
                  icon
                  @click="hideClass(item.items[0].raw.tag_class.pk)"
                  v-bind="props"
                  variant="text"
                  color="lighterIcons"
                  density="comfortable"
                >
                  <v-icon size="small"
                    >{{
                      classIdToObj.has(item.items[0].raw.tag_class.pk) &&
                      classIdToObj.get(item.items[0].raw.tag_class.pk).hidden
                        ? "fas fa-eye-slash"
                        : "fas fa-eye"
                    }}
                  </v-icon>
                </v-btn>
              </template>
              <span>{{
                classIdToObj.has(item.items[0].raw.tag_class.pk) &&
                classIdToObj.get(item.items[0].raw.tag_class.pk).hidden
                  ? $t("tag_class_hidden")
                  : $t("tag_class_visible")
              }}</span>
            </v-tooltip>
            <v-tooltip
              location="bottom"
              max-width="600px"
              v-if="canCreateTagsInClass(item.items[0].raw.tag_class.pk)"
            >
              <template #activator="{ props }">
                <AddTagButton
                  v-bind="props"
                  :tag-class="classIdToObj.get(item.items[0].raw.tag_class.pk)"
                  icon
                  small
                  comfortable
                  color="lighterIcons"
                  text
                  @saved="fetchTags()"
                ></AddTagButton>
              </template>
              {{ $t("labels.new_tag") }}
            </v-tooltip>
          </td>
        </tr>
      </template>
    </v-data-table>
    <v-dialog v-model="showEditDialog" max-width="720px">
      <EditTagWidget
        :tag="editedTag"
        @close="showEditDialog = false"
        @saved="onSave()"
        ref="tagEditWidget"
      ></EditTagWidget>
    </v-dialog>
    <v-dialog v-model="showClassEditDialog" max-width="720px">
      <EditTagClassWidget
        :tag-class="editedTagClass"
        @close="showClassEditDialog = false"
        @saved="onClassSave()"
      ></EditTagClassWidget>
    </v-dialog>
  </div>
</template>

<script>
import cancellation from "@/mixins/cancellation";
import TagChip from "@/components/tags/TagChip";
import AddTagButton from "@/components/tags/AddTagButton";
import EditTagWidget from "@/components/tags/EditTagWidget";
import { mapActions } from "vuex";
import AddTagClassButton from "@/components/tags/AddTagClassButton";
import tagAccessLevels from "@/mixins/tagAccessLevels";
import EditTagClassWidget from "@/components/tags/EditTagClassWidget";
import TagClassScopeWidget from "@/components/tags/TagClassScopeWidget";
import { accessLevels } from "@/libs/tags";
import stateTracking from "@/mixins/stateTracking";

export default {
  name: "TagListWidget",
  components: {
    TagClassScopeWidget,
    EditTagClassWidget,
    AddTagClassButton,
    EditTagWidget,
    AddTagButton,
    TagChip,
  },
  mixins: [cancellation, tagAccessLevels, stateTracking],

  props: {
    performanceThreshold: {
      // if the number of tags is above this, we don't show the tag chips
      // and try to optimize the performance
      type: Number,
      default: 200,
    },
  },

  data() {
    return {
      tags: [],
      loading: false,
      search: "",
      groupByClass: true,
      editedTag: null,
      showEditDialog: false,
      tagScope: "",
      tagClasses: [],
      tagClassesLoading: false,
      editedTagClass: null,
      showClassEditDialog: false,
      showClass: false,
      showSystemTags: false,
      // table state
      orderBy: [{ key: null, order: this.orderDesc ? "desc" : "asc" }],
      orderDesc: false,
      page: 1,
      itemsPerPage: -1,
      // state tracking support
      watchedAttrs: [
        {
          name: "orderBy",
          type: Object,
        },
        {
          name: "orderDesc",
          type: Boolean,
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
          name: "search",
          type: String,
        },
        {
          name: "tagScope",
          type: String,
        },
        {
          name: "showClass",
          type: Boolean,
        },
        {
          name: "showSystemTags",
          type: Boolean,
        },
        {
          name: "groupByClass",
          type: Boolean,
          alwaysTrack: true,
        },
      ],
    };
  },

  computed: {
    headers() {
      return [
        {
          title: this.$i18n.t("labels.tag_name"),
          value: "name",
          key: "name",
          groupable: false,
        },
        // {
        //   title: this.$i18n.t("labels.tag_class"),
        //   value: "_group_sorter",
        //   key: "_group_sorter",
        // },
        {
          title: this.$i18n.t("labels.tag_can_see"),
          value: "can_see",
          key: "can_see",
          groupable: false,
        },
        {
          title: this.$i18n.t("labels.tag_can_assign"),
          value: "can_assign",
          key: "can_assign",
          groupable: false,
        },
        {
          title: this.$i18n.t("title_fields.actions"),
          value: "actions",
          groupable: false,
          sortable: false,
        },
      ];
    },
    visibleTags() {
      let out = this.tags;
      if (this.tagScope) {
        out = out.filter((tag) => tag.tag_class.scope === this.tagScope);
      }
      if (!this.showSystemTags) {
        out = out.filter((tag) => tag.can_assign !== accessLevels.SYSTEM);
      }
      return out;
    },
    visibleTagClasses() {
      let out = this.tagClasses;
      if (this.tagScope) {
        out = out.filter((tc) => tc.scope === this.tagScope);
      }
      if (!this.showSystemTags) {
        out = out.filter((tc) => tc.can_create_tags !== accessLevels.SYSTEM);
      }
      return out;
    },
    tagScopes() {
      return [
        { value: "", title: this.$t("labels.all_tags") },
        { value: "title", title: this.$t("title") },
        { value: "platform", title: this.$t("platform") },
        { value: "organization", title: this.$t("organization") },
      ];
    },
    classIdToObj() {
      let map = new Map();
      this.tags.forEach((tag) => map.set(tag.tag_class.pk, tag.tag_class));
      this.tagClasses.forEach((tc) => map.set(tc.pk, tc));
      return map;
    },
    optimizePerformance() {
      return this.visibleTags.length > this.performanceThreshold;
    },
  },

  methods: {
    ...mapActions({ showSnackbar: "showSnackbar" }),
    async fetchTags() {
      this.loading = true;
      this.tags = [];
      let reply = await this.http({ url: "/api/tags/tag/" });
      this.loading = false;
      if (!reply.error) {
        this.tags = reply.response.data;
        this.tags.forEach(
          (item) =>
            (item._group_sorter = `${item.tag_class.name}-${item.tag_class.pk}`),
        );
      }
    },
    async fetchTagClasses() {
      this.tagClassesLoading = true;
      // load tag classes for which user can create tags
      // and tag classes that have at least one tag which is visible
      // for the user (e.g. system tags)
      const reply = await this.http({
        url: "/api/tags/tag-class/visible-tags/?include_managed=true",
      });
      this.tagClassesLoading = false;
      if (!reply.error) {
        this.tagClasses = reply.response.data;
      }
    },
    editTag(tag) {
      this.editedTag = tag;
      if (this.$refs.tagEditWidget) {
        this.$refs.tagEditWidget.reload();
      }
      this.showEditDialog = true;
    },
    editClass(clsId) {
      this.editedTagClass = this.classIdToObj.get(clsId);
      this.showClassEditDialog = true;
    },
    async deleteTag(tag) {
      const reply = await this.http({
        url: `/api/tags/tag/${tag.pk}/${tag.tag_class.scope}/`,
      });
      if (!reply.error) {
        const goOn = await this.$confirm(
          this.$tc("delete_tag_item_count", reply.response.data.count, {
            tag: tag.name,
          }),
          {
            title: this.$t("confirm_tag_delete"),
            buttonTrueText: this.$t("actions.delete"),
            buttonFalseText: this.$t("actions.cancel"),
            color: "warning",
            icon: "fa fa-warning",
          },
        );
        if (goOn) {
          const reply = await this.http({
            url: `/api/tags/tag/${tag.pk}/`,
            method: "delete",
          });
          if (!reply.error) {
            this.showSnackbar({
              content: this.$t("tag_delete_success", { tag: tag.name }),
              color: "success",
            });
            this.tags = this.tags.filter((item) => item.pk !== tag.pk);
          }
        }
      }
    },
    async deleteClass(clsId) {
      const cls = this.classIdToObj.get(clsId);
      const tagCount = this.tags.filter(
        (tag) => tag.tag_class.pk === cls.pk,
      ).length;
      const goOn = await this.$confirm(
        this.$tc("delete_tag_class_tag_count", tagCount, cls),
        {
          title: this.$t("confirm_tag_class_delete"),
          buttonTrueText: this.$t("actions.delete"),
          buttonFalseText: this.$t("actions.cancel"),
          color: "warning",
          icon: "fa fa-warning",
        },
      );
      if (goOn) {
        const reply = await this.http({
          url: `/api/tags/tag-class/${cls.pk}/`,
          method: "delete",
        });
        if (!reply.error) {
          this.showSnackbar({
            content: this.$t("tag_class_delete_success", {
              tag_class: cls.name,
            }),
            color: "success",
          });
          this.tags = this.tags.filter((item) => item.tag_class.pk !== cls.pk);
          this.tagClasses = this.tagClasses.filter(
            (item) => item.pk !== cls.pk,
          );
        }
      }
    },
    async onSave() {
      this.editedTag = null;
      this.showEditDialog = false;
      await this.fetchTags();
    },
    async onClassSave() {
      this.editedTagClass = null;
      this.showClassEditDialog = false;
      await Promise.all([this.fetchTags(), this.fetchTagClasses()]);
    },
    groupingFn(items, groupBy, groupDesc) {
      // we want to add empty groups for tag-classes without tag,
      // so we need a custom grouping function
      let groups = new Map();
      items.forEach((tag) => {
        if (!groups.has(tag.tag_class.pk)) {
          groups.set(tag.tag_class.pk, [tag]);
        } else {
          groups.get(tag.tag_class.pk).push(tag);
        }
      });
      this.visibleTagClasses.forEach((tc) => {
        if (
          !groups.has(tc.pk) &&
          (this.tagScope === "" || tc.scope === this.tagScope)
        ) {
          groups.set(tc.pk, []);
        }
      });
      let out = [];
      groups.forEach((tags, clsId) =>
        out.push({
          name: clsId,
          items: tags,
        }),
      );
      return out;
    },
    async hideClass(clsId) {
      const nowHidden = this.classIdToObj.get(clsId).hidden;
      let result = await this.http({
        url: `/api/tags/tag-class/${clsId}/hide/`,
        method: "post",
        data: { hidden: !nowHidden },
      });
      if (!result.error) {
        for (let tc of this.tagClasses) {
          if (tc.pk === clsId) {
            tc.hidden = result.response.data.hidden;
            break;
          }
        }
      }
    },
    canCreateTagsInClass(group) {
      return (
        this.classIdToObj.has(group) &&
        this.classIdToObj.get(group).user_score >=
          this.classIdToObj.get(group).can_create_tags
      );
    },
  },

  mounted() {
    this.fetchTags();
    this.fetchTagClasses();
  },
};
</script>

<style scoped lang="scss">
:deep(
    .v-table
      > .v-table__wrapper
      > table
      > thead
      > tr
      > th:first-child
      > .v-data-table-header__content
  ) {
  visibility: hidden;
}
.tag {
  padding: 0.5rem 0.75rem;
  border-radius: 1.5rem;

  span.fa {
    font-size: 0.75rem;
  }
}
.group_header {
  background: #eeeeeeee;
}

.group_column {
  width: 30px;
  padding-right: 0 !important;
}

.tag_column {
  padding-left: 0px !important;
}
</style>
