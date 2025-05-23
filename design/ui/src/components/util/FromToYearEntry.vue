<i18n lang="yaml">
en:
  year_start: Start year
  year_end: End year
cs:
  year_start: Počáteční rok
  year_end: Koncový rok
</i18n>

<template>
  <div class="d-flex">
    <YearEntry
      class="pr-2"
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
    modelValue: { required: true, type: Object, default: () => ({}) },
    startLabel: { required: false, type: String, default: null },
    endLabel: { required: false, type: String, default: null },
    disabled: { required: false, type: Boolean, default: false },
    yearsBack: { required: false, type: Number, default: 10 },
  },

  data() {
    return {
      startYear: this.modelValue.start?.year ?? null,
      endYear: this.modelValue.end?.year ?? null,
    };
  },

  computed: {
    availableStartYears() {
      let year = new Date().getFullYear();
      let result = [...Array(this.yearsBack).keys()].map((i) => ({
        text: year - i,
        modelValue: year - i,
        disabled: this.endYear && this.endYear < year - i,
      }));
      return result;
    },
    availableEndYears() {
      let year = new Date().getFullYear();
      let result = [...Array(this.yearsBack).keys()].map((i) => ({
        text: year - i,
        modelValue: year - i,
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
      this.$emit("update:modelValue", this.dateRange);
    },
    endYear() {
      this.$emit("update:modelValue", this.dateRange);
    },
  },
};
</script>

<style scoped></style>
