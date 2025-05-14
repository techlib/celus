<i18n lang="yaml">
en:
  mode: History
  modes:
    all: All
    current: Current
    success_and_current: Successful + current
  tooltips:
    all: Displays all attempts matching criteria
    current: Discards attempts for older versions of SUSHI credentials
    success_and_current: All attempts for the current version of SUSHI credentials and successful attempts for older versions

cs:
  mode: Historie
  modes:
    all: Všechny
    current: Aktuální
    success_and_current: Úspěšné + aktuální
  tooltips:
    all: Zobrazí všechny pokusy odpovídající tomuto zobrazení
    current: Vynechá pokusy, které byly vytvořeny se staršími verzemi přihlašovacích údajů k SUSHI
    success_and_current: Všechny pokusy pro aktuální verzi přihlašovacích údajů SUSHI + úspěšné pokusy pro starší verze
</i18n>

<template>
  <v-select
    :items="modeList"
    v-model="mode"
    :label="$t('mode')"
    :hint="`${mode.tooltip}`"
    return-object
  ></v-select>
</template>

<script>
export default {
  name: "FetchAttemptModeFilter",
  props: {
    modelValue: { required: true, type: String },
  },

  data() {
    let modeList = [
      {
        value: "current",
        title: this.$t("modes.current"),
        tooltip: this.$t("tooltips.current"),
      },
      {
        value: "success_and_current",
        title: this.$t("modes.success_and_current"),
        tooltip: this.$t("tooltips.success_and_current"),
      },
      {
        value: "all",
        title: this.$t("modes.all"),
        tooltip: this.$t("tooltips.all"),
      },
    ];
    return {
      modeList: modeList,
      mode: modeList[1],
    };
  },

  watch: {
    mode() {
      this.$emit("update:modelValue", this.modelValue);
    },
  },
};
</script>
