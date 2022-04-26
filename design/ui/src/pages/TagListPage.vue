<i18n lang="yaml" src="../locales/common.yaml"></i18n>

<template>
  <v-container fluid>
    <v-row>
      <v-col class="pb-0">
        <h2>{{ $t("pages.tags") }}</h2>
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <TagListWidget />
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import TagListWidget from "@/components/tags/TagListWidget";
export default {
  name: "TagListPage",

  components: { TagListWidget },

  data() {
    return {};
  },
};
</script>
