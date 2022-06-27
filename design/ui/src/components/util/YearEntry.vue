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
    :disabled="disabled"
    clearable
    :rules="[switchedMonths]"
    clear-icon="fa fa-times"
    prepend-icon="fa-calendar-alt"
    @change="$emit('input', year)"
  >
  </v-select>
</template>

<script>
export default {
  name: "YearEntry",
  props: {
    value: { required: true },
    label: { required: false, default: "", type: String },
    disabled: { required: false, type: Boolean, default: false },
    overlappingYears: { required: false },
    years: { required: true },
  },
  data() {
    return {
      year: this.value,
    };
  },
  methods: {
    switchedMonths() {
      return !this.overlappingYears || this.$t("overlapping_years");
    },
  },
};
</script>

<style scoped></style>
