<i18n lang="yaml">
en:
  yes: Yes
  no: No

cs:
  yes: Ano
  no: Ne
</i18n>

<template>
  <v-tooltip bottom>
    <template v-slot:activator="{ on }">
      <v-icon
        small
        :color="value ? trueColor : falseColor"
        :class="extraClasses"
        v-on="on"
      >
        {{ value ? trueIcon : falseIcon }}
      </v-icon>
    </template>
    <span>{{ value ? trueTooltipFinal : falseTooltipFinal }}</span>
  </v-tooltip>
</template>

<script>
export default {
  name: "CheckMark",
  props: {
    value: { required: true, type: Boolean },
    extraClasses: { required: false, type: String },
    trueColor: { default: "secondary darken-2" },
    falseColor: { default: "secondary" },
    trueIcon: { default: "far fa-check-square" },
    falseIcon: { default: "far fa-square" },
    trueTooltip: { default: null },
    falseTooltip: { default: null },
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
