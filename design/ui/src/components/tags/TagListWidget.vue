<i18n lang="yaml" src="../../locales/common.yaml"></i18n>
<i18n lang="yaml">
en:
  confirm_tag_delete: Confirm tag delete
  delete_tag_item_count: Do you wan't to delete tag "{tag}" used by {count} item? | Do you wan't to delete tag "{tag}" used by {count} items?
  tag_delete_success: Tag "{tag}" was successfully deleted
</i18n>

<template>
  <div>
    <v-data-table
      :items="visibleTags"
      :headers="headers"
      :loading="loading"
      item-key="pk"
      :items-per-page="50"
      :footer-props="{ itemsPerPageOptions: [50, 100, -1] }"
      :search="search"
      :group-by="groupByClass ? '_group_sorter' : null"
      :custom-group="groupingFn"
    >
      <template #top="">
        <v-row class="d-flex">
          <v-col class="align-self-center" cols="auto">
            <AddTagClassButton @saved="fetchTagClasses()" small />
          </v-col>
          <v-col class="align-self-center" cols="auto">
            <AddTagButton @saved="fetchTags()" small />
          </v-col>
          <v-spacer></v-spacer>
          <v-col>
            <v-select
              :items="tagScopes"
              v-model="tagScope"
              :label="$t('labels.tag_scope')"
            />
          </v-col>
          <v-col>
            <v-switch v-model="showClass" label="Show class" />
          </v-col>
          <v-col>
            <v-switch
              v-model="groupByClass"
              :label="$t('labels.group_by_class')"
            />
          </v-col>
          <v-col>
            <v-text-field
              v-model="search"
              clearable
              :label="$t('labels.search')"
            ></v-text-field>
          </v-col>
        </v-row>
      </template>

      <template #item.name="{ item }">
        <TagChip :tag="item" :show-class="showClass" link />
      </template>

      <template #item._group_sorter="{ item }">
        {{ item.tag_class.name }}
        <TagClassScopeWidget
          :scope="item.tag_class.scope"
          class="pl-3 text-caption text--disabled"
        />
      </template>

      <template #item.can_see="{ item }">
        <span class="text-caption">{{
          tagAccessLevelToText[item.can_see]
        }}</span>
      </template>

      <template #item.can_assign="{ item }">
        <span class="text-caption">{{
          tagAccessLevelToText[item.can_assign]
        }}</span>
      </template>

      <template #item.actions="{ item }">
        <v-btn @click="editTag(item)" small icon
          ><v-icon small>fa fa-edit</v-icon></v-btn
        >
        <v-btn @click="deleteTag(item)" small icon
          ><v-icon small>fa fa-trash</v-icon></v-btn
        >
      </template>

      <template
        #group.header="{ items, isOpen, toggle, remove, headers, group }"
      >
        <td>
          <v-btn icon @click="toggle" small>
            <v-icon x-small>{{ isOpen ? "fa fa-minus" : "fa fa-plus" }}</v-icon>
          </v-btn>
          <span class="font-weight-light pr-2"
            >{{ $t("labels.tag_class") }}:</span
          >
          <span class="font-weight-bold" v-if="classIdToObj.has(group)">{{
            classIdToObj.get(group).name
          }}</span>
        </td>
        <td :colspan="headers.length - 2">
          <span class="font-weight-light pr-2"
            >{{ $t("labels.tag_scope") }}:</span
          >
          <span class="font-weight-bold" v-if="classIdToObj.has(group)">
            <TagClassScopeWidget
              :scope="classIdToObj.get(group).scope"
              icon-color="#a0a0a0"
              class="text--secondary"
            />
          </span>
        </td>
        <td>
          <v-btn
            v-if="
              classIdToObj.has(group) && classIdToObj.get(group).user_can_modify
            "
            small
            icon
            @click="editClass(group)"
          >
            <v-icon small>fa-edit</v-icon>
          </v-btn>
        </td>
      </template>
    </v-data-table>
    <v-dialog v-model="showEditDialog" max-width="720px">
      <EditTagWidget
        :tag="editedTag"
        @close="showEditDialog = false"
        @saved="onSave()"
        ref="tag_edit_widget"
      />
    </v-dialog>
    <v-dialog v-model="showClassEditDialog" max-width="720px">
      <EditTagClassWidget
        :tag-class="editedTagClass"
        @close="showClassEditDialog = false"
        @saved="onClassSave()"
      />
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
  mixins: [cancellation, tagAccessLevels],

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
    };
  },

  computed: {
    headers() {
      return [
        {
          text: this.$i18n.t("labels.tag_name"),
          value: "name",
          groupable: false,
        },
        {
          text: this.$i18n.t("labels.tag_class"),
          value: "_group_sorter",
        },
        {
          text: this.$i18n.t("labels.tag_can_see"),
          value: "can_see",
          groupable: false,
        },
        {
          text: this.$i18n.t("labels.tag_can_assign"),
          value: "can_assign",
          groupable: false,
        },
        {
          text: this.$i18n.t("title_fields.actions"),
          value: "actions",
          groupable: false,
          sortable: false,
        },
      ];
    },
    visibleTags() {
      if (this.tagScope) {
        return this.tags.filter((tag) => tag.tag_class.scope === this.tagScope);
      }
      return this.tags;
    },
    tagScopes() {
      return [
        { value: "", text: this.$t("labels.all_tags") },
        { value: "title", text: this.$t("title") },
        { value: "platform", text: this.$t("platform") },
        { value: "organization", text: this.$t("organization") },
      ];
    },
    classIdToObj() {
      let map = new Map();
      this.tags.forEach((tag) => map.set(tag.tag_class.pk, tag.tag_class));
      this.tagClasses.forEach((tc) => map.set(tc.pk, tc));
      return map;
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
            (item._group_sorter = `${item.tag_class.name}-${item.tag_class.pk}`)
        );
      }
    },
    async fetchTagClasses() {
      this.tagClassesLoading = true;
      const reply = await this.http({ url: "/api/tags/tag-class/" });
      this.tagClassesLoading = false;
      if (!reply.error) {
        this.tagClasses = reply.response.data;
      }
    },
    editTag(tag) {
      this.editedTag = tag;
      if (this.$refs.tag_edit_widget) {
        this.$refs.tag_edit_widget.reload();
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
          }
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
      this.tagClasses.forEach((tc) => {
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
        })
      );
      return out;
    },
  },

  mounted() {
    this.fetchTags();
    this.fetchTagClasses();
  },
};
</script>

<style scoped></style>
