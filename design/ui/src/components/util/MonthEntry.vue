<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml">
en:
  multiple-values: Several different values
cs:
  multiple-values: Více různých hodnot
</i18n>

<template>
  <v-menu
    v-model="menuOpen"
    transition="scale-transition"
    offset-y
    style="min-width: 290px"
    :disabled="disabled"
  >
    <template v-slot:activator="{ props }">
      <v-text-field
        v-model="monthText"
        :label="label"
        readonly
        v-bind="props"
        :clearable="clearable"
        clear-icon="fa fa-times"
        :disabled="disabled"
        @click:clear="dateUpdated"
        :error-messages="validatePair ? errorMessages : []"
      >
        <template #prepend>
          <v-icon color="#aaaaaa">far fa-calendar-alt</v-icon>
        </template>
      </v-text-field>
    </template>
    <VueDatePicker
      v-model="date"
      :locale="$i18n.locale"
      month-picker
      inline
      auto-apply
    ></VueDatePicker>
  </v-menu>
</template>

<script>
import { ymDateFormat, ymDateParse } from "@/libs/dates";

export default {
  name: "MonthEntry",

  emits: ["update:modelValue"],

  props: {
    modelValue: { required: true, type: [String, null], default: null },
    label: { required: false, default: "", type: String },
    disabled: { required: false, type: Boolean, default: false },
    clearable: { required: false, type: Boolean, default: true },
    minMonth: { required: false, type: String, default: null },
    maxMonth: { required: false, type: String, default: null },
    multipleValues: { required: false, type: Boolean, default: false },
    validatePair: { required: false, type: Boolean, default: false },
  },

  data() {
    let showMultipleValues = this.multipleValues;
    return {
      menuOpen: false,
      date: null,
      showMultipleValues: showMultipleValues,
    };
  },

  computed: {
    monthText: {
      get() {
        if (this.showMultipleValues) {
          return this.$t("multiple-values");
        }
        if (this.date)
          return ymDateFormat(new Date(this.date.year, this.date.month));
        return "";
      },
      set(value) {
        if (value) {
          let date = ymDateParse(value);
          this.date = {
            year: date.getFullYear(),
            month: date.getMonth(),
          };
        } else {
          this.date = null;
        }
      },
    },
    minMonthDate() {
      if (this.minMonth) {
        return ymDateParse(this.minMonth);
      }
      return null;
    },
    maxMonthDate() {
      if (this.maxMonth) {
        return ymDateParse(this.maxMonth);
      }
      return null;
    },
    errorMessages() {
      if (this.modelValue) {
        const dateValue = ymDateParse(this.modelValue);
        return this.maxMonthDate !== null && dateValue > this.maxMonthDate
          ? this.$t("errors.error_start_after_end")
          : null;
      }
    },
  },

  methods: {
    dateUpdated() {
      this.showMultipleValues = false;
      this.$emit("update:modelValue", this.monthText);
    },
  },

  watch: {
    date() {
      this.dateUpdated();
    },
    modelValue: {
      immediate: true,
      handler() {
        if (this.modelValue) {
          let date = ymDateParse(this.modelValue);
          this.date = {
            year: date.getFullYear(),
            month: date.getMonth(),
          };
        } else {
          this.date = null;
        }
      },
    },
  },
};
</script>

<style scoped></style>
