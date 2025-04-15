<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<template>
  <span>{{ text }}</span>
</template>

<script>
import { ymDateFormat } from "@/libs/dates";

export default {
  name: "DateRangeText",

  props: {
    start: { required: true },
    end: { required: true },
    separator: { type: String, default: " – " }, // en dash
  },

  computed: {
    text() {
      let start = this.startDate;
      let end = this.endDate;
      if (this.start || this.end) {
        if (start === end) {
          return `${start}`;
        }
        return `${start}${this.separator}${end}`;
      }
      return "";
    },
    startDate() {
      if (this.start) {
        return ymDateFormat(this.start);
      }
      return "";
    },
    endDate() {
      if (this.end) {
        return ymDateFormat(this.end);
      }
      return this.$t("labels.today");
    },
  },
};
</script>

<style scoped></style>
