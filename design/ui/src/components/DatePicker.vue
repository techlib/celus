<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<template>
  <v-menu
    v-model="menuOpen"
    transition="scale-transition"
    offset-y
    min-width="290px"
    :disabled="disabled"
  >
    <template v-slot:activator="{ props }">
      <v-text-field
        :model-value="selectedDateText"
        :label="label"
        v-bind="props"
        :style="styleField"
        readonly
        :error-messages="validatePair ? errorMessages : []"
      >
        <template v-slot:prepend>
          <slot name="prepend">
            <v-icon>{{ prependIcon }}</v-icon>
          </slot>
        </template>
        <template v-if="$slots.append" v-slot:append>
          <slot name="append"></slot>
        </template>
        <template v-if="$slots['prepend-inner']" v-slot:prepend-inner>
          <slot name="prepend-inner"></slot>
        </template>
        <template v-if="$slots['append-inner']" v-slot:append-inner>
          <slot name="append-inner"></slot>
        </template>
      </v-text-field>
    </template>
    <VueDatePicker
      v-model="dateValue"
      :locale="$i18n.locale"
      month-picker
      inline
      auto-apply
      :max-date="maxDateLimit"
    >
    </VueDatePicker>
  </v-menu>
</template>

<script>
export default {
  name: "DatePicker",
  props: {
    modelValue: { default: null, type: [String, Object] },
    maxDate: { default: null },
    minDate: { default: null },
    disabled: { type: Boolean },
    label: { type: String },
    hideDetails: { type: String },
    prependIcon: { type: String, default: "fa fa-calendar" },
    styleField: { type: String },
    validatePair: { type: Boolean, default: false },
    maxDateLimit: { default: null },
  },

  emits: ["validityUpdated"],

  data() {
    return {
      menuOpen: false,
      dateValue: this.modelValue,
    };
  },
  computed: {
    selectedDateText() {
      if (
        typeof this.dateValue === "object" &&
        this.dateValue !== null &&
        "month" in this.dateValue
      ) {
        const monthStr = (this.dateValue.month + 1).toString().padStart(2, "0");
        return `${this.dateValue.year}-${monthStr}`;
      } else {
        return this.dateValue;
      }
    },
    errorMessages() {
      if (this.modelValue) {
        const dateValue =
          typeof this.modelValue === "object"
            ? new Date(this.modelValue.year, this.modelValue.month)
            : this.modelValue;
        const errors = [];
        if (dateValue > this.maxDate) {
          errors.push(this.$t("errors.error_start_after_end"));
        }
        this.$emit("validityUpdated", errors.length > 0);
        return errors;
      }
    },
  },
  watch: {
    dateValue: {
      handler(newValue) {
        if (
          newValue &&
          (newValue.month !== this.modelValue.month ||
            newValue.year !== this.modelValue.year)
        ) {
          this.$emit("update:modelValue", newValue);
        }
      },
      deep: true,
    },
    modelValue: {
      handler(newValue) {
        if (
          newValue &&
          (newValue.month !== this.dateValue?.month ||
            newValue.year !== this.dateValue?.year)
        ) {
          this.dateValue = { ...newValue };
        }
      },
      deep: true,
    },
  },
};
</script>

<style scoped>
.justify-content-between {
  justify-content: space-between;
}
.justify-content-end {
  justify-content: flex-end;
}
</style>
