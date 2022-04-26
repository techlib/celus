<i18n lang="yaml" src="../../locales/common.yaml"></i18n>

<template>
  <span>
    <v-icon x-small :color="iconColor" class="pb-1">{{ iconName }}</v-icon>
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
        ? "fa-copy"
        : this.scope === "platform"
        ? "fa-list-alt"
        : "fa-university";
    },
  },
};
</script>
