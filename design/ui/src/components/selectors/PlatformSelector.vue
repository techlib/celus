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
      <v-tooltip bottom max-width="600px" v-if="badge(item)">
        <template #activator="{ on }">
          <span>{{ item.name }}</span>
          <v-badge
            inline
            :content="$t(badge(item).content)"
            :color="badge(item).color"
          >
            <template v-slot:badge>
              <span v-on="on">{{ $t(badge(item).content) }}</span>
            </template>
          </v-badge>
        </template>
        <span>{{ $t(badge(item).tooltip) }}</span>
      </v-tooltip>
      <span v-else>
        {{ item.name }}
      </span>
    </template>
  </v-autocomplete>
</template>
<script>
import { badge } from "@/libs/sources.js";

export default {
  name: "PlatformSelector",

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

  methods: {
    badge,
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
