<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<template>
  <span>
    <v-icon size="x-small" :color="iconColor" class="pb-1">{{
      iconName
    }}</v-icon>
    {{ $t(scope) }}
  </span>
</template>

<script>
export default {
  name: "TagClassScopeWidget",

  props: {
    scope: {
      type: String,
      validator(value) {
        return ["title", "platform", "organization"].includes(value);
      },
    },
    iconColor: { type: String, default: "#bbbbbb" },
  },

  computed: {
    iconName() {
      return this.scope === "title"
        ? "far fa-copy"
        : this.scope === "platform"
          ? "fa fa-list-alt"
          : "fa fa-university";
    },
  },
};
</script>
