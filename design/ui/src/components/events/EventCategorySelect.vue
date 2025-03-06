<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<template>
  <v-select
    v-model="filterCategory"
    :items="items"
    :label="$t('events.category')"
    item-title="text"
    :clearable="!showAll"
    clear-icon="fas fa-times"
  >
    <template #item="{ item, props }">
      <v-list-item v-bind="props" title="">
        <v-list-item-title>
          {{ item.raw.text }}
          <span v-if="item.count" class="float-right text-caption">{{
            item.count
          }}</span>
        </v-list-item-title>
      </v-list-item>
    </template>
  </v-select>
</template>

<script>
export default {
  name: "EventCategorySelect",

  props: {
    value: {},
    showAll: { type: Boolean, default: false },
    categories: { type: Map, default: null, required: false },
  },

  data() {
    return {
      filterCategory: null,
      allCategories: new Map([
        ["general", null],
        ["overlap", null],
        ["platform", null],
        ["sushi", null],
        ["tags", null],
      ]),
    };
  },

  computed: {
    items() {
      let categories = this.categories ?? this.allCategories;
      let out = [];
      categories.forEach((count, category) =>
        out.push({
          text: this.$t(`event_category.${category}`),
          value: category,
          count,
        }),
      );
      if (this.showAll) {
        out.unshift({ text: this.$t("options.all"), value: null, count: null });
      }
      return out;
    },
  },

  watch: {
    filterCategory() {
      this.$emit("input", this.filterCategory);
    },
    value() {
      this.filterCategory = this.value;
    },
  },
};
</script>
