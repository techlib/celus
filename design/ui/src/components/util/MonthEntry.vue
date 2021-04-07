<template>
  <v-menu
    v-model="menuOpen"
    transition="scale-transition"
    offset-y
    min-width="290px"
  >
    <template v-slot:activator="{ on }">
      <v-text-field
        v-model="date"
        :label="label"
        prepend-icon="fa-calendar-alt"
        readonly
        v-on="on"
        clearable
        clear-icon="fa fa-times"
      ></v-text-field>
    </template>
    <v-date-picker
      v-model="date"
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
  },

  data() {
    return {
      menuOpen: false,
      date: this.value,
    };
  },

  watch: {
    date() {
      this.$emit("input", this.date);
    },
  },
};
</script>

<style scoped></style>
