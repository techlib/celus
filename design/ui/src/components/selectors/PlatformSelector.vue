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
    :filter="filter"
    :return-object="returnObject"
    :dense="dense"
    :height="height"
    ref="platformSelector"
    clear-icon="fa-times"
  >
    <template v-slot:item="{ item }">
      <v-list-item-content>
        <v-list-item-title>
          <ItemBadge :item="item" tag="span" />
        </v-list-item-title>
        <v-list-item-subtitle>
          {{ item.short_name }}
        </v-list-item-subtitle>
      </v-list-item-content>
    </template>

    <template #prepend-item>
      <slot name="prepend"></slot>
    </template>
  </v-autocomplete>
</template>
<script>
import ItemBadge from "@/components/util/ItemBadge";
import AddPlatformButton from "@/components/AddPlatformButton.vue";
import { all } from "mathjs";

export default {
  name: "PlatformSelector",

  components: {
    AddPlatformButton,
    ItemBadge,
  },

  props: {
    platforms: { type: Array, required: true },
    loading: { default: false, type: Boolean },
    value: { default: null, type: Number | Object },
    label: { default: null, type: String },
    returnObject: { default: false, type: Boolean },
    dense: { default: false, type: Boolean },
    height: { default: null, type: Number | String },
    allowCreate: { default: false, type: Boolean },
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

  methods: {
    all() {
      return all;
    },
    filter(item, queryText) {
      const text = item.name.toLowerCase();
      const shortName = item.short_name.toLowerCase();
      const query = queryText.toLowerCase();
      return text.includes(query) || shortName.includes(query);
    },
    validate() {
      this.$refs.platformSelector.validate();
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
