<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<i18n lang="yaml"></i18n>

<template>
  <v-container fluid>
    <v-row>
      <v-col class="pb-0" cols="auto">
        <h2>{{ $t("pages.counter_registry") }}</h2>
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <CounterRegistryPlatformListWidget></CounterRegistryPlatformListWidget>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import CounterRegistryPlatformListWidget from "@/components/registry/CounterRegistryPlatformListWidget";

export default {
  name: "CounterRegistryPage",

  mixins: [],

  components: {
    CounterRegistryPlatformListWidget,
  },
};
</script>

<style lang="scss" scoped></style>
