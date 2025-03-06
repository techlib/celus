<i18n lang="yaml">
en:
  overlapping_years: End year ought not to be before the start year
cs:
  overlapping_years: Koncový rok by neměl být před počátečním rokem
</i18n>

<template>
  <v-select
    class="shrink"
    v-model="year"
    :items="years"
    :label="label"
    item-title="text"
    item-value="modelValue"
    :item-props="isDisabled"
    :disabled="disabled"
    clearable
    density="default"
    :rules="[switchedMonths]"
    clear-icon="fa fa-times"
    prepend-icon="far fa-calendar-alt"
    @update:modelValue="updateYear"
  >
  </v-select>
</template>

<script>
export default {
  name: "YearEntry",
  props: {
    modelValue: { required: true, type: [Number, null], default: null },
    label: { required: false, default: "", type: String },
    disabled: { required: false, type: Boolean, default: false },
    overlappingYears: { required: false },
    years: { required: true },
  },
  data() {
    return {
      year: this.modelValue,
    };
  },
  methods: {
    switchedMonths() {
      return !this.overlappingYears || this.$t("overlapping_years");
    },
    updateYear(value) {
      this.$emit("update:modelValue", value);
    },
    isDisabled(item) {
      return { disabled: item.disabled };
    },
  },
  watch: {
    modelValue(newValue) {
      this.year = newValue;
    },
  },
};
</script>

<style scoped></style>
