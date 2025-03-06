<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<template>
  <v-tooltip max-width="600px" location="bottom">
    <template #activator="{ props }">
      <v-icon :color="color" v-bind="props" :size="small ? 'x-small' : ''">
        {{ icon }} {{ fixedWidth ? "fa fa-fw" : "" }}
      </v-icon>
    </template>
    <span>{{
      importance ? $t(`event_importance.${importance}`) : $t("options.all")
    }}</span>
  </v-tooltip>
</template>

<script>
export default {
  name: "EventImportanceIcon",

  props: {
    importance: { required: true },
    fixedWidth: { type: Boolean, default: false },
    small: { type: Boolean, default: false },
  },

  computed: {
    importanceNumber() {
      return parseInt(this.importance);
    },
    color() {
      return `${this.baseColor} lighten-2`;
    },
    baseColor() {
      switch (this.importanceNumber) {
        case 20:
          return "orange";
        case 10:
          return "blue";
        default:
          return "grey";
      }
    },
    icon() {
      switch (this.importanceNumber) {
        case 20:
          return "fa fa-exclamation-triangle";
        case 10:
          return "fa fa-info-circle";
        default:
          return "fa fa-expand";
      }
    },
  },
};
</script>
