<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<template>
  <v-tooltip max-width="600px" location="bottom">
    <template #activator="{ props }">
      <span :class="bold ? 'font-weight-bold' : ''" v-bind="props">{{
        $t(`event_category.${item.category}`)
      }}</span>
    </template>
    {{ $t(`event_category_desc.${item.category}`) }}
  </v-tooltip>
</template>

<script>
export default {
  name: "EventCategoryMark",
  props: {
    item: {},
    bold: {
      type: Boolean,
      default: false,
    },
  },
};
</script>
