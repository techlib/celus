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
      <slot name="activator" :props="props"></slot>
    </template>
    <VueDatePicker
      :max-date="maxDate"
      :min-date="minDate"
      v-model="dateValue"
      :locale="$i18n.locale"
      month-picker
      inline
      auto-apply
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
  },
  data() {
    return {
      menuOpen: false,
      dateValue: this.modelValue,
    };
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

:deep(.v-input__details) {
  display: none;
}
</style>
