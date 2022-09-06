<i18n lang="yaml" src="../../locales/common.yaml"></i18n>

<template>
  <v-autocomplete
    v-model="selectedTags"
    :items="visibleTags"
    item-text="name"
    item-value="pk"
    :multiple="!singleTag"
    :deletable-chips="!singleTag"
    :label="labelToShow"
    clearable
    clear-icon="fa-times"
    item-disabled="disabled"
  >
    <template #item="{ item }">
      <v-list-item-content>
        <v-list-item-title class="d-flex align-center justify-space-between">
          <TagChip :tag="item" v-if="item.disabled" hide-icon disabled />
          <TagChip :tag="item" v-else />
          <span class="text-caption">{{ item.tag_class.name }}</span>
        </v-list-item-title>
        <v-list-item-subtitle v-if="item.disabled" class="text-caption">
          {{ $t("labels.tag_exclusive_already_present") }}
        </v-list-item-subtitle>
      </v-list-item-content>
    </template>

    <template #selection="{ item }">
      <!-- tooltips on tags work strange in autocomplete and the whole tag
      sometimes disappears, so we disable the tooltip here -->
      <TagChip
        :tag="item"
        small
        hide-icon
        hide-tooltip
        removable
        @remove="unselect(item.pk)"
      />
    </template>

    <template #prepend v-if="tooltip">
      <v-tooltip bottom>
        <template #activator="{ on }">
          <v-icon v-on="on">fa fa-info-circle</v-icon>
        </template>
        {{ tooltip }}
      </v-tooltip>
    </template>
  </v-autocomplete>
</template>
<script>
import cancellation from "@/mixins/cancellation";
import TagChip from "@/components/tags/TagChip";

export default {
  name: "TagSelector",
  components: { TagChip },
  mixins: [cancellation],

  props: {
    value: {},
    hiddenTags: { type: Array, default: () => [] },
    usedExclusiveClasses: { type: Array, default: () => [] },
    label: { type: String, default: "" },
    tooltip: { type: String, default: "" },
    assignableOnly: { type: Boolean, default: false },
    // if this selector is not used to assign tags, dontCheckExclusive can
    // be used to allow selection of more than one exclusive tag
    dontCheckExclusive: { type: Boolean, default: false },
    scope: {
      type: String,
      validator(value) {
        return ["title", "platform", "organization"].includes(value);
      },
      required: true,
    },
    singleTag: { type: Boolean, default: false },
  },

  data() {
    return {
      tags: [],
    };
  },

  computed: {
    selectedTags: {
      get() {
        return this.value;
      },
      set(value) {
        this.$emit("input", value);
      },
    },
    selectedExclusiveClasses() {
      let value = Array.isArray(this.value) ? this.value : [this.value];
      return this.tags
        .filter((tag) => tag.tag_class.exclusive)
        .filter((tag) => value.includes(tag.pk))
        .map((tag) => tag.tag_class.pk);
    },
    visibleTags() {
      return this.tags
        .filter((tag) => !this.hiddenTags.includes(tag.pk))
        .map((tag) => ({
          ...tag,
          disabled:
            !this.dontCheckExclusive &&
            (this.usedExclusiveClasses.includes(tag.tag_class.pk) ||
              this.selectedExclusiveClasses.includes(tag.tag_class.pk)),
        }));
    },
    labelToShow() {
      if (this.label) {
        return this.label;
      }
      if (this.singleTag) {
        return this.$t("labels.tag");
      }
      return this.$t("labels.tags");
    },
  },

  methods: {
    async fetchTags() {
      this.loading = true;
      this.tags = [];
      let params = { scope: this.scope };
      if (this.assignableOnly) {
        params["assignable_only"] = 1;
      }
      let reply = await this.http({ url: "/api/tags/tag/", params: params });
      this.loading = false;
      if (!reply.error) {
        this.tags = reply.response.data;
      }
    },
    unselect(itemId) {
      this.selectedTags = this.selectedTags.filter((item) => item !== itemId);
    },
  },

  mounted() {
    this.fetchTags();
  },
};
</script>
