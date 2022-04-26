<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<template>
  <v-container fluid>
    <v-row>
      <v-col>
        <h2>{{ $t("pages.title_lists") }}</h2>
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <TaggingBatchList />
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import TaggingBatchList from "@/components/tagging-batches/TaggingBatchList";
export default {
  name: "TaggingBatchesPage",
  components: { TaggingBatchList },
};
</script>

<style scoped></style>
