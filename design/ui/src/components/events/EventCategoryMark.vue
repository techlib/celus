<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<template>
  <v-tooltip bottom max-width="600px">
    <template #activator="{ on }">
      <span v-on="on" :class="bold ? 'font-weight-bold' : ''">{{
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
