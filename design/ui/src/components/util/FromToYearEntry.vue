<i18n lang="yaml">
en:
  year_start: Start year
  year_end: End year
cs:
  year_start: Počáteční rok
  year_end: Koncový rok
</i18n>

<template>
  <div class="d-flex flex-wrap">
    <YearEntry
      class="pr-4"
      v-model="startYear"
      :label="textStart"
      :disabled="disabled"
      :overlapping-years="overlappingYears"
      :years="availableStartYears"
    ></YearEntry>
    <YearEntry
      v-model="endYear"
      :label="textEnd"
      :disabled="disabled"
      :overlapping-years="overlappingYears"
      :years="availableEndYears"
    ></YearEntry>
  </div>
</template>

<script>
import YearEntry from "@/components/util/YearEntry";
import isEqual from "lodash/isEqual";

export default {
  name: "FromToYearEntry",

  components: { YearEntry },

  props: {
    value: { required: true, type: Object },
    startLabel: { required: false, type: String, default: null },
    endLabel: { required: false, type: String, default: null },
    disabled: { required: false, type: Boolean, default: false },
    yearsBack: { required: false, type: Number, default: 10 },
  },

  data() {
    return {
      startYear: this.value.start?.year ?? null,
      endYear: this.value.end?.year ?? null,
    };
  },

  computed: {
    availableStartYears() {
      let year = new Date().getFullYear();
      let result = [...Array(this.yearsBack).keys()].map((i) => ({
        text: year - i,
        value: year - i,
        disabled: this.endYear && this.endYear < year - i,
      }));
      return result;
    },
    availableEndYears() {
      let year = new Date().getFullYear();
      let result = [...Array(this.yearsBack).keys()].map((i) => ({
        text: year - i,
        value: year - i,
        disabled: this.startYear && this.startYear > year - i,
      }));
      return result;
    },
    textStart() {
      return this.startLabel ?? this.$t("year_start");
    },
    textEnd() {
      return this.endLabel ?? this.$t("year_end");
    },
    overlappingYears() {
      return this.startYear && this.endYear && this.startYear > this.endYear;
    },
    dateRange() {
      return {
        start: this.startYear ? `${this.startYear}-01` : null,
        end: this.endYear ? `${this.endYear}-12` : null,
      };
    },
  },

  watch: {
    startYear() {
      this.$emit("input", this.dateRange);
    },
    endYear() {
      this.$emit("input", this.dateRange);
    },
    value() {
      if (!isEqual(this.value, this.dateRange)) {
        this.startYear = this.value.start?.year ?? null;
        this.endYear = this.value.end?.year ?? null;
      }
    },
  },
};
</script>

<style scoped></style>
