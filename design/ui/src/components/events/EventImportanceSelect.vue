<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<template>
  <v-select
    v-model="filterImportance"
    :items="items"
    :label="$t('events.importance')"
    :clearable="!showAll"
    clear-icon="fas fa-times"
    item-value="value"
  >
    <template #selection="{ item }">
      <EventImportanceIcon :importance="item.value" small></EventImportanceIcon>
      <span class="ml-2">{{ item.raw.text }}</span>
    </template>
    <template #item="{ item, props }">
      <v-list-item v-bind="props" title="">
        <v-list-item-title>
          <EventImportanceIcon
            :importance="item.raw.value"
          ></EventImportanceIcon>
          <span class="ml-2">{{ item.raw.text }}</span>
          <span v-if="item.raw.count" class="float-right text-caption">{{
            item.count
          }}</span>
        </v-list-item-title>
      </v-list-item>
    </template>
  </v-select>
</template>

<script>
import EventImportanceIcon from "@/components/events/EventImportanceIcon.vue";

export default {
  name: "EventImportanceSelect",
  components: { EventImportanceIcon },

  props: {
    value: {},
    showAll: { type: Boolean, default: false },
    importancies: { type: Map, default: null, required: false },
  },

  data() {
    return {
      filterImportance: null,
      allCategories: new Map([
        [10, null],
        [20, null],
      ]),
    };
  },

  computed: {
    items() {
      let categories = this.importancies ?? this.allCategories;
      let out = [];
      categories.forEach((count, category) => {
        out.push({
          text: this.$t(`event_importance.${category}`),
          value: category,
          count,
        });
      });
      if (this.showAll) {
        out.unshift({ text: this.$t("options.all"), value: null, count: null });
      }
      return out;
    },
  },

  watch: {
    filterImportance() {
      this.$emit("input", this.filterImportance);
    },
    value() {
      this.filterImportance = this.value;
    },
  },
};
</script>
