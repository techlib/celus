<i18n src="@/locales/common.yaml" lang="yaml"></i18n>

<template>
  <v-data-table
    :items="platforms"
    item-key="pk"
    :headers="headers"
    sort-by="name"
  >
    <template #item.actions="{ item }">
      <v-tooltip bottom>
        <template #activator="{ on }">
          <v-btn
            v-on="on"
            icon
            :to="{
              name: 'platform-upload-data',
              params: { platformId: item.pk },
              query: { method: 'raw' },
            }"
          >
            <v-icon>fa-upload</v-icon>
          </v-btn>
        </template>
        {{ $t("actions.upload_data") }}
      </v-tooltip>
    </template>
  </v-data-table>
</template>

<script>
import cancellation from "@/mixins/cancellation";
import stateTracking from "@/mixins/stateTracking";
import { mapState } from "vuex";

export default {
  name: "SupportedNonCounterPlatformsList",

  mixins: [cancellation, stateTracking],

  data() {
    return {
      platforms: [],
      loading: false,
    };
  },

  computed: {
    ...mapState({
      selectedOrganizationId: "selectedOrganizationId",
    }),
    headers() {
      let ret = [
        { text: this.$t("title_fields.short_name"), value: "short_name" },
        { text: this.$t("title_fields.name"), value: "name" },
        { text: this.$t("title_fields.actions"), value: "actions" },
      ];
      return ret;
    },
  },

  methods: {
    async fetchPlatforms() {
      this.loading = true;
      let resp = await this.http({
        url: `/api/organization/${this.selectedOrganizationId}/all-platform/`,
      });
      if (!resp.error) {
        this.platforms = resp.response.data.filter((p) => p.has_raw_parser);
      }
    },
  },

  watch: {
    selectedOrganizationId() {
      this.fetchPlatforms();
    },
  },

  mounted() {
    this.fetchPlatforms();
  },
};
</script>

<style scoped></style>
