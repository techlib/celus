<template>
  <v-tooltip location="bottom" v-if="tag.desc && !hideTooltip">
    <template #activator="{ props }">
      <span v-bind="props">
        <TagChipSimple :tag="tag" v-bind="$attrs"></TagChipSimple>
      </span>
    </template>
    {{ tag.desc }}
  </v-tooltip>
  <TagChipSimple v-else :tag="tag" v-bind="$attrs"></TagChipSimple>
</template>

<script>
import TagChipSimple from "@/components/tags/TagChipSimple";

export default {
  name: "TagChip",

  components: { TagChipSimple },

  props: {
    tag: { required: true, type: Object },
    hideTooltip: {
      default: false,
      type: Boolean,
    },
  },
};
</script>
