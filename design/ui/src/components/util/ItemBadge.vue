<i18n lang="yaml" src="@/locales/sources.yaml"></i18n>
<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<template>
  <component :is="tag">
    <v-tooltip bottom max-width="600px" v-if="badge(item)">
      <template #activator="{ on }">
        <span :class="innerClass">{{ item.name }}</span>
        <v-badge
          :inline="badgeInline"
          :content="$t(badge(item).content)"
          :color="badge(item).color"
          :class="badgeClass"
        >
          <template v-slot:badge>
            <span v-on="on">{{ $t(badge(item).content) }}</span>
          </template>
        </v-badge>
      </template>
      <span>{{ $t(badge(item).tooltip) }}</span>
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

  methods: {
    badge,
  },

};

</script>
