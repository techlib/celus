<i18n lang="yaml" src="@/locales/sources.yaml"></i18n>

<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<template>
  <v-autocomplete
    :items="platforms"
    item-value="pk"
    item-title="name"
    :label="shownLabel"
    v-model="selectedPlatform"
    :loading="loading"
    clearable
    :custom-filter="filter"
    :height="height"
    ref="platformSelector"
    clear-icon="fas fa-times"
    density="default"
    :menu-props="{ eager: true }"
    :return-object="returnObject"
  >
    <template v-slot:item="{ props, item }">
      <v-list-item v-bind="props" title="">
        <div class="d-flex flex-column justify-lg-start">
          <ItemBadge :item="item.raw" tag="span"></ItemBadge>
          <span class="subtitle">
            {{ item.raw.short_name }}
          </span>
        </div>
      </v-list-item>
    </template>
    <template #prepend-item>
      <slot name="prepend"></slot>
    </template>
  </v-autocomplete>
</template>

<script>
import ItemBadge from "@/components/util/ItemBadge";
import { all } from "mathjs";

export default {
  name: "PlatformSelector",

  components: {
    ItemBadge,
  },

  props: {
    platforms: { type: Array, required: true },
    loading: { default: false, type: Boolean },
    modelValue: { default: null, type: [Number, Object] },
    label: { default: null, type: String },
    returnObject: { default: false, type: Boolean },
    dense: { default: false, type: Boolean },
    height: { default: null, type: [Number, String] },
  },

  data() {
    return {
      selectedPlatform: this.modelValue,
    };
  },

  computed: {
    shownLabel() {
      return this.label || this.$t("title_fields.select_platform");
    },
  },

  methods: {
    all() {
      return all;
    },
    filter(itemTitle, queryText, item) {
      const text = item.raw.name.toLowerCase();
      const shortName = item.raw.short_name.toLowerCase();
      const query = queryText.toLowerCase();
      return text.includes(query) || shortName.includes(query);
    },
    validate() {
      this.$refs.platformSelector.validate();
    },
  },

  watch: {
    selectedPlatform() {
      this.$emit("update:modelValue", this.selectedPlatform);
    },
    modelValue() {
      this.selectedPlatform = this.modelValue;
    },
  },
};
</script>

<style scoped>
.subtitle {
  font-size: 80%;
  color: rgba(0, 0, 0, 0.5);
}
</style>
