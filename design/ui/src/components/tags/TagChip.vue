<template>
  <v-tooltip bottom v-if="tag.desc && !hideTooltip">
    <template #activator="{ on }">
      <span v-on="on">
        <TagChipSimple v-on="$listeners" :tag="tag" v-bind="$attrs" />
      </span>
    </template>
    {{ tag.desc }}
  </v-tooltip>

  <TagChipSimple v-else v-on="$listeners" :tag="tag" v-bind="$attrs" />
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
