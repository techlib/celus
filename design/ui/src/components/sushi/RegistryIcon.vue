<i18n lang="yaml" src="@/locales/common.yaml" />

<template>
  <v-tooltip bottom max-width="600px">
    <template #activator="{ on }">
      <v-icon v-on="on" small color="counterRegistry">fa-registered</v-icon>
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
