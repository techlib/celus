<i18n lang="yaml" src="../../locales/common.yaml"></i18n>

<template>
  <v-card :elevation="elevation">
    <v-card-title
      class="py-2"
      style="font-variant: small-caps; font-size: 82.5%"
    >
      {{ $t("labels.tags") }}
      <v-spacer></v-spacer>
      <span>
        <v-btn icon @click="editing = !editing">
          <v-icon small>fa {{ editing ? "fa-check" : "fa-edit" }}</v-icon>
        </v-btn>
      </span>
    </v-card-title>
    <v-card-text>
      <v-skeleton-loader v-if="loading" type="paragraph" />
      <div v-else-if="tags.length">
        <div v-for="tag in tags" :key="tag.pk" class="pb-1">
          <TagChip
            :tag="tag"
            :show-class="showClass"
            :removable="editing && tag.user_can_assign"
            @remove="removeTag"
          />
        </div>
      </div>
      <div v-else-if="!editing">
        {{ $t("labels.no_tags") }}
      </div>

      <div v-if="editing">
        <TagSelector
          v-model="tagsToAdd"
          :hidden-tags="usedTagIds"
          :used-exclusive-classes="usedExclusiveClasses"
          assignable-only
          :scope="scope"
        />
      </div>
    </v-card-text>
  </v-card>
</template>
<script>
import cancellation from "@/mixins/cancellation";
import TagChip from "@/components/tags/TagChip";
import TagSelector from "@/components/tags/TagSelector";

export default {
  name: "TagCard",
  components: { TagSelector, TagChip },
  mixins: [cancellation],

  props: {
    scope: {
      required: true,
      type: String,
      validator(value) {
        return ["title", "platform", "organization"].includes(value);
      },
    },
    itemId: {
      required: true,
      type: Number,
    },
    showClass: {
      default: false,
      type: Boolean,
    },
    elevation: {
      default: 2,
      type: Number,
    },
  },

  data() {
    return {
      loading: false,
      tags: [],
      editing: false,
      tagsToAdd: [],
    };
  },

  computed: {
    tagsUrl() {
      if (this.scope && this.itemId)
        return `/api/tags/tag/?item_type=${this.scope}&item_id=${this.itemId}`;
      return null;
    },
    usedTagIds() {
      return this.tags.map((tag) => tag.pk);
    },
    usedExclusiveClasses() {
      return this.tags
        .filter((tag) => tag.tag_class.exclusive)
        .map((tag) => tag.tag_class.pk);
    },
  },

  methods: {
    async loadTags() {
      if (this.tagsUrl) {
        this.tags = [];
        this.loading = true;
        let result = await this.http({ url: this.tagsUrl });
        if (!result.error) {
          this.tags = result.response.data;
        }
        this.loading = false;
      }
    },
    async removeTag(tagId) {
      await this.http({
        url: `/api/tags/tag/${tagId}/${this.scope}/remove/`,
        method: "delete",
        data: { item_id: this.itemId },
      });
      this.tags = this.tags.filter((item) => item.pk !== tagId);
    },
  },

  watch: {
    tagsUrl() {
      this.loadTags();
    },
    async editing() {
      if (!this.editing) {
        // we just turned off editing, so we must save the selected tags
        if (this.tagsToAdd.length) {
          let promises = [];
          for (const tag of this.tagsToAdd) {
            promises.push(
              this.http({
                url: `/api/tags/tag/${tag}/${this.scope}/add/`,
                method: "post",
                data: { item_id: this.itemId, scope: this.scope },
              })
            );
          }
          await Promise.all(promises);
          this.$emit("update");
          this.tagsToAdd = [];
          await this.loadTags();
        }
      }
    },
  },

  mounted() {
    this.loadTags();
  },
};
</script>
