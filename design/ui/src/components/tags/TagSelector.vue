<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<template>
  <v-autocomplete
    v-model="selectedTags"
    :items="visibleTags"
    item-value="pk"
    item-title="name"
    :multiple="!singleTag"
    :closable-chips="!singleTag"
    :label="labelToShow"
    clearable
    chips
    :item-props="(item) => ({ disabled: item.disabled })"
    :disabled="disabled"
    :filter="filter"
    :no-data-text="$t('labels.no_tags_available')"
    :menu-props="{ eager: true }"
    hide-selected
  >
    <template #item="{ item, props }">
      <v-list-item v-bind="props">
        <template #title>
          <v-list-item-title class="d-flex align-center justify-space-between">
            <TagChip
              v-if="item.raw.disabled"
              :tag="item.raw"
              hide-icon
              disabled
            ></TagChip>
            <TagChip v-else :tag="item.raw"></TagChip>
            <span class="text-caption">{{ item.raw.tag_class.name }}</span>
          </v-list-item-title>
        </template>
        <template #subtitle>
          <v-list-item-subtitle v-if="item.raw.disabled" class="text-caption">
            {{ $t("labels.tag_exclusive_already_present") }}
          </v-list-item-subtitle>
        </template>
      </v-list-item>
    </template>
    <template v-slot:chip="{ props, item }">
      <!-- tooltips on tags work strange in autocomplete and the whole tag
      sometimes disappears, so we disable the tooltip here -->
      <TagChip
        v-bind="props"
        :tag="item.raw"
        small
        :hide-icon="!singleTag"
        hide-tooltip
        :removable="!singleTag && !disabled"
        :show-class="singleTag"
        @remove="unselect(item.raw.pk)"
      ></TagChip>
    </template>
    <template #prepend v-if="tooltip">
      <v-tooltip location="bottom" max-width="480px">
        <template #activator="{ props }">
          <v-icon v-bind="props">fa fa-info-circle</v-icon>
        </template>
        {{ tooltip }}
      </v-tooltip>
    </template>
    <template #prepend v-else-if="showIcon">
      <v-icon size="small">fa fa-tag fa-fw</v-icon>
    </template>
    <template v-slot:append-item v-if="allowCreate">
      <v-list-item>
        <AddTagButton
          small
          class="mb-1"
          @saved="addNewTag"
          :scope="scope"
          outlined
        ></AddTagButton>
      </v-list-item>
    </template>
  </v-autocomplete>
</template>

<script>
import cancellation from "@/mixins/cancellation";
import TagChip from "@/components/tags/TagChip";
import AddTagButton from "@/components/tags/AddTagButton.vue";

export default {
  name: "TagSelector",
  components: { AddTagButton, TagChip },
  mixins: [cancellation],

  props: {
    modelValue: {},
    disabled: { type: Boolean, default: false },
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
      validator(modelValue) {
        return ["title", "platform", "organization"].includes(modelValue);
      },
      required: true,
    },
    singleTag: { type: Boolean, default: false },
    allowCreate: { type: Boolean, default: false },
    showIcon: { type: Boolean, default: false },
  },

  data() {
    return {
      tags: [],
      show: false,
    };
  },

  computed: {
    selectedTags: {
      get() {
        return this.modelValue;
      },
      set(modelValue) {
        this.$emit("update:modelValue", modelValue);
      },
    },
    selectedExclusiveClasses() {
      let modelValue = Array.isArray(this.modelValue)
        ? this.value
        : [this.modelValue];
      return this.tags
        .filter((tag) => tag.tag_class.exclusive)
        .filter((tag) => modelValue.includes(tag.pk))
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
    filter(item, queryText) {
      const name = item.name.toLowerCase();
      const className = item.tag_class.name.toLowerCase();

      const words = queryText.toLowerCase().split(/ /);
      for (let word of words) {
        if (name.indexOf(word) < 0 && className.indexOf(word) < 0) return false;
      }
      return true;
    },
    addNewTag(newTag) {
      // add new tag to the end of the list of tags
      // we want to add it to the end so that it is visible right up from
      // the button for adding new tags
      this.tags.push(newTag);
    },
  },

  mounted() {
    this.fetchTags();
  },
};
</script>

<style lang="scss" scoped>
:deep .v-field__input {
  padding-bottom: 5px;
}
</style>
