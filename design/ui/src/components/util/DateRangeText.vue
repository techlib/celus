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
  },

  computed: {
    text() {
      let start = this.startDate;
      let end = this.endDate;
      if (this.start || this.end) {
        return `${start} - ${end}`;
      }
      return "";
    },
    startDate() {
      if (this.start) {
        return ymDateFormat(this.start);
        // if ("month" in this.start) {
        //   const month = this.start.month;
        //   const year = this.start.year;
        //   return `${year} - ${month}`;
        // } else {
        //   const month = (this.start.getMonth() + 1).toString().padStart(2, "0");
        //   const year = this.start.getFullYear();
        //   return `${year} - ${month}`;
        // }
        // return this.start;
      }
      return "";
    },
    endDate() {
      if (this.end) {
        // return ymDateFormat(this.end);
        if ("month" in this.end) {
          const month = this.end.month;
          const year = this.end.year;
          return `${year}-${month}`;
        } else {
          const month = (this.end.getMonth() + 1).toString().padStart(2, "0");
          const year = this.end.getFullYear();
          return `${year}-${month}`;
        }
        // return this.end;
      }
      return this.$t("labels.today");
    },
  },
};
</script>

<style scoped></style>
