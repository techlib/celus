<i18n lang="yaml">
en:
  yes: Yes
  no: No

cs:
  yes: Ano
  no: Ne
</i18n>

<template>
  <v-tooltip location="bottom">
    <template v-slot:activator="{ props }">
      <v-icon
        :size="iconSize"
        :color="modelValue ? trueColor : falseColor"
        :class="extraClasses"
        v-bind="props"
      >
        {{ modelValue ? trueIcon : falseIcon }}
      </v-icon>
    </template>
    <span>{{ modelValue ? trueTooltipFinal : falseTooltipFinal }}</span>
  </v-tooltip>
</template>

<script>
export default {
  name: "CheckMark",
  props: {
    modelValue: { required: true, type: Boolean },
    extraClasses: { required: false, type: String },
    trueColor: { default: "grey darken-2" },
    falseColor: { default: "grey" },
    trueIcon: { default: "far fa-check-square" },
    falseIcon: { default: "far fa-square" },
    trueTooltip: { default: null },
    falseTooltip: { default: null },
    iconSize: { default: "small", type: String },
  },

  computed: {
    trueTooltipFinal() {
      return this.trueTooltip ? this.trueTooltip : this.$t("yes");
    },
    falseTooltipFinal() {
      return this.falseTooltip ? this.falseTooltip : this.$t("no");
    },
  },
};
</script>

<style scoped></style>
