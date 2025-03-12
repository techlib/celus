<i18n lang="yaml">
en:
  has_data: Has data
  platform: Platform

cs:
  has_data: Má data
  platform: Platforma
</i18n>

<template>
  <v-data-table
    :headers="headers"
    :items="platforms"
    :loading="loading"
    :items-per-page="-1"
    :hide-default-footer="true"
    v-model:sort-by="orderBy"
  >
    <template #item.name="{ item }">
      <span v-text="item.name" :class="{ bold: item.has_data }"></span>
    </template>
    <template #item.has_data="{ item }">
      <CheckMark
        true-color="warning"
        false-color="grey"
        :model-value="item.has_data"
      ></CheckMark>
    </template>
  </v-data-table>
</template>

<script>
import { mapActions, mapState } from "vuex";
import CheckMark from "@/components/util/CheckMark";

export default {
  name: "UndefinedInterestWidget",
  components: {
    CheckMark,
  },
  data() {
    return {
      platforms: [],
      loading: false,
      orderBy: [{ key: "has_data", order: "desc" }],
    };
  },
  computed: {
    ...mapState({
      organizationId: "selectedOrganizationId",
    }),
    headers() {
      return [
        {
          title: this.$t("platform"),
          value: "name",
          key: "name",
        },
        {
          title: this.$t("has_data"),
          value: "has_data",
          key: "has_data",
        },
      ];
    },
  },
  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
      fetchNoInterestPlatforms: "fetchNoInterestPlatforms",
    }),
    async fetchPlatforms() {
      if (this.organizationId) {
        this.loading = true;
        this.platforms = await this.fetchNoInterestPlatforms();
        this.loading = false;
      }
    },
  },
  mounted() {
    this.fetchPlatforms();
  },
};
</script>

<style scoped>
span.bold {
  font-weight: bold;
}
</style>
