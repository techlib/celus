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

  computed: {
    availableStartYears() {
      let year = new Date().getFullYear();
      let result = [...Array(this.yearsBack).keys()].map((i) => ({
        text: year - i,
        value: year - i,
        disabled: this.endYear < year - i,
      }));
      return result;
    },
    availableEndYears() {
      let year = new Date().getFullYear();
      let result = [...Array(this.yearsBack).keys()].map((i) => ({
        text: year - i,
        value: year - i,
        disabled: this.startYear > year - i,
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
      return this.startYear > this.endYear;
    },
    startYear: {
      get() {
        return this.stripMonthAndRetypeToInt(this.value.start);
      },
      set(newValue) {
        this.$emit("input", {
          start: newValue ? `${newValue}-01` : "",
          end: this.endYear,
        });
      },
    },
    endYear: {
      get() {
        return this.stripMonthAndRetypeToInt(this.value.end);
      },
      set(newValue) {
        this.$emit("input", {
          start: this.startYear,
          end: newValue ? `${newValue}-12` : "",
        });
      },
    },
  },

  methods: {
    stripMonthAndRetypeToInt(yearMonth) {
      if (yearMonth) {
        return new Date(yearMonth + "").getFullYear();
      }
    },
  },
};
</script>

<style scoped></style>
