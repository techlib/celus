<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<template>
  <v-tooltip location="bottom" max-width="600px">
    <template #activator="{ props }">
      <v-icon v-bind="props" size="small" color="counterRegistry"
        >fa fa-registered</v-icon
      >
    </template>
    <div>
      <div class="bold" v-text="$t('registry_info')"></div>
      <span>{{ text }}</span>
    </div>
  </v-tooltip>
</template>

<script>
export default {
  name: "RegistryIcon",

  props: {
    text: {
      type: String,
      default: "",
    },
  },
};
</script>
