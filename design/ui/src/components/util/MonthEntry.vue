<template>
  <v-menu
    v-model="menuOpen"
    transition="scale-transition"
    offset-y
    min-width="290px"
    :disabled="disabled"
  >
    <template v-slot:activator="{ on }">
      <v-text-field
        v-model="month"
        :label="label"
        prepend-icon="fa-calendar-alt"
        readonly
        v-on="on"
        clearable
        clear-icon="fa fa-times"
        :disabled="disabled"
      ></v-text-field>
    </template>
    <v-date-picker
      v-model="month"
      type="month"
      no-title
      scrollable
      :locale="$i18n.locale"
      :allowed-dates="allowedMonths"
    >
    </v-date-picker>
  </v-menu>
</template>

<script>
export default {
  name: "MonthEntry",

  props: {
    value: { required: true },
    label: { required: false, default: "", type: String },
    allowedMonths: { required: false, type: Function },
    disabled: { required: false, type: Boolean, default: false },
  },

  data() {
    return {
      menuOpen: false,
      month: this.value,
    };
  },

  watch: {
    month() {
      this.$emit("input", this.month);
    },
  },
};
</script>

<style scoped></style>
