<template>
  <v-container fluid>
    <v-row>
      <v-col>
        <StoredReportsTable />
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import StoredReportsTable from "@/components/reporting/StoredReportsTable";
export default {
  name: "FlexibleReportsPage",
  components: { StoredReportsTable },
};
</script>

<style scoped></style>
