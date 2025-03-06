<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<template>
  <v-container fluid>
    <v-row>
      <v-col>
        <h2>{{ $t("pages.management_commands") }}</h2>
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <ManagementCommandList></ManagementCommandList>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import ManagementCommandList from "@/components/admin/ManagementCommandList.vue";
export default {
  name: "ManagementCommandsPage",
  components: {
    ManagementCommandList,
  },

  data() {
    return {};
  },
};
</script>

<style scoped></style>
