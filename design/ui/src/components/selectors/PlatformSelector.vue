<i18n lang="yaml" src="@/locales/sources.yaml"></i18n>
<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<template>
  <v-autocomplete
    autofocus
    :items="platforms"
    item-value="pk"
    item-text="name"
    :label="shownLabel"
    v-model="selectedPlatform"
    :loading="loading"
    clearable
  >
    <template v-slot:item="{ item }">
      <ItemBadge :item="item" tag="span" />
    </template>
  </v-autocomplete>
</template>
<script>
import ItemBadge from "@/components/util/ItemBadge";

export default {
  name: "PlatformSelector",

  components: {
    ItemBadge,
  },

  props: {
    platforms: { type: Array, required: true },
    loading: { default: false, type: Boolean },
    value: { default: null, type: Number },
    label: { default: null, type: String },
  },

  data() {
    return {
      selectedPlatform: this.value,
    };
  },

  computed: {
    shownLabel() {
      return this.label || this.$t("title_fields.select_platform");
    },
  },

  watch: {
    selectedPlatform() {
      this.$emit("input", this.selectedPlatform);
    },
    value() {
      this.selectedPlatform = this.value;
    },
  },
};
</script>
