<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<template>
  <v-card :elevation="elevation">
    <v-card-title
      class="py-2 d-flex align-center"
      style="font-variant: small-caps; font-size: 82.5%"
    >
      {{ $t("labels.tags") }}
      <v-spacer></v-spacer>
      <span>
        <v-btn
          icon
          @click="
            editing = !editing;
            sendTag();
          "
          variant="plain"
        >
          <v-icon size="x-small"
            >fa {{ editing ? "fa fa-check" : "fas fa-edit" }}</v-icon
          >
        </v-btn>
      </span>
    </v-card-title>
    <v-card-text>
      <v-skeleton-loader v-if="loading" type="paragraph"></v-skeleton-loader>
      <div v-else-if="tags.length" class="d-flex flex-wrap">
        <span v-for="tag in tags" :key="tag.pk" class="pr-1 pb-1">
          <TagChip
            :tag="tag"
            :show-class="showClass"
            :removable="editing && tag.user_can_assign"
            @remove="removeTag"
          ></TagChip>
        </span>
      </div>
      <div v-else-if="!editing">
        {{ $t("labels.no_tags") }}
      </div>
      <div v-if="editing">
        <TagSelector
          v-model="tagToAdd"
          :hidden-tags="usedTagIds"
          :used-exclusive-classes="usedExclusiveClasses"
          assignable-only
          :scope="scope"
          single-tag
          allow-create
        ></TagSelector>
      </div>
    </v-card-text>
  </v-card>
</template>

<script>
import cancellation from "@/mixins/cancellation";
import TagChip from "@/components/tags/TagChip";
import TagSelector from "@/components/tags/TagSelector";
import { mapActions } from "vuex";

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
      tagToAdd: null,
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
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    sendTag() {
      this.$emit("update", this.tags, this.itemId);
    },
    async loadTags(triggerLoading = true) {
      if (this.tagsUrl) {
        if (triggerLoading) this.loading = true;
        let result = await this.http({ url: this.tagsUrl });
        if (!result.error) {
          this.tags = result.response.data;
        } else {
          this.tags = [];
        }
        this.loading = false;
      }
    },
    async removeTag({ tagId }) {
      await this.http({
        url: `/api/tags/tag/${tagId}/${this.scope}/remove/`,
        method: "delete",
        data: { item_id: this.itemId },
      });
      this.tags = this.tags.filter((item) => item.pk !== tagId);
    },
    async addTag({ tagId }) {
      await this.http({
        url: `/api/tags/tag/${tagId}/${this.scope}/add/`,
        method: "post",
        data: { item_id: this.itemId, scope: this.scope },
      });
    },
  },

  watch: {
    tagsUrl() {
      this.loadTags();
    },
    async tagToAdd() {
      if (this.tagToAdd) {
        const reply = await this.addTag({ tagId: this.tagToAdd });
        if (reply?.error) {
          await this.showSnackbar({
            content: "Error assigning tag.",
            color: "error",
          });
        }
      }
      this.tagToAdd = null;
      // we do not want the loading animation as it makes the UI jump
      await this.loadTags(false);
    },
  },

  mounted() {
    this.loadTags();
  },
};
</script>
