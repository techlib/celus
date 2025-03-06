<i18n lang="yaml" src="@/locales/sources.yaml"></i18n>

<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<template>
  <component :is="tag">
    <v-tooltip max-width="600px" v-if="badgeInfo" location="bottom">
      <template #activator="{ props }">
        <span :class="innerClass">{{ item.name }}</span>
        <v-badge
          :inline="badgeInline"
          :content="$t(badgeInfo.content)"
          :color="badgeInfo.color"
          :class="badgeClass"
        >
          <template v-slot:badge>
            <span v-bind="props">{{ $t(badgeInfo.content) }}</span>
          </template>
        </v-badge>
      </template>
      <span>{{ $t(badgeInfo.tooltip) }}</span>
    </v-tooltip>
    <span :class="innerClass" v-else>
      {{ item.name }}
    </span>
  </component>
</template>

<script>
import { badge } from "@/libs/sources.js";

export default {
  props: {
    badgeClass: { default: "", type: String },
    badgeInline: { default: true, type: Boolean },
    innerClass: { default: "", type: String },
    tag: { default: "span", type: String },
    item: { type: Object, required: true },
  },

  computed: {
    badgeInfo() {
      return badge(this.item);
    },
  },
};
</script>

<style>
.badge_manual {
  height: 30px;
}
</style>
