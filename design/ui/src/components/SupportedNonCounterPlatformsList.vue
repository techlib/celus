<i18n src="@/locales/common.yaml" lang="yaml"></i18n>

<i18n lang="yaml">
en:
  knowledgebase_article: Detailed information about the format from CELUS knowledgebase

cs:
  knowledgebase_article: Podrobné informace o formátu ve znalostní bázi CELUS
</i18n>

<template>
  <v-data-table
    :items="platforms"
    item-key="pk"
    :headers="headers"
    v-model:sort-by="sortBy"
    :items-per-page="-1"
    :search="search"
    :loading="loading"
    class="auto-table"
  >
    <template #[`item.actions`]="{ item }">
      <v-tooltip location="bottom">
        <template #activator="{ props }">
          <v-btn
            v-bind="props"
            variant="text"
            :to="{
              name: 'platform-upload-data',
              params: { platformId: item.pk },
              query: { method: 'raw' },
            }"
            color="secondary"
            size="small"
          >
            <v-icon size="small" class="pr-5">fa fa-upload</v-icon>
            {{ $t("actions.upload_data") }}
          </v-btn>
        </template>
        {{ $t("actions.upload_data") }}
      </v-tooltip>
    </template>
    <template #[`item.info`]="{ item }">
      <v-tooltip location="bottom" max-width="600px">
        <template #activator="{ props }">
          <v-btn
            v-if="item.knowledgebase && item.knowledgebase.notes_url"
            v-bind="props"
            :href="item.knowledgebase.notes_url"
            target="_blank"
            variant="text"
            color="tertiary"
            size="small"
          >
            <v-icon size="small" color="info" class="mr-2"
              >fas fa-info-circle</v-icon
            >
            {{ $t("title_fields.info") }}
          </v-btn>
        </template>
        {{ $t("knowledgebase_article") }}
      </v-tooltip>
    </template>
    <template #top>
      <v-row>
        <v-spacer></v-spacer>
        <v-col>
          <v-text-field
            v-model="search"
            :label="$t('labels.search')"
            clearable
            clear-icon="fa fa-times"
            append-inner-icon="fa fa-search"
          ></v-text-field>
        </v-col>
      </v-row>
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
      sortBy: [{ key: "name", order: "asc" }],
      search: "",
      // state tracking support
      watchedAttrs: [
        {
          name: "search",
          type: String,
        },
      ],
    };
  },

  computed: {
    ...mapState({
      selectedOrganizationId: "selectedOrganizationId",
    }),
    headers() {
      let ret = [
        {
          title: this.$t("title_fields.short_name"),
          value: "short_name",
          key: "short_name",
          sortable: true,
        },
        {
          title: this.$t("title_fields.name"),
          value: "name",
          key: "name",
          sortable: true,
        },
        {
          title: this.$t("title_fields.knowledgebase"),
          value: "info",
          key: "info",
          sortable: true,
        },
        { title: this.$t("title_fields.actions"), value: "actions" },
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
        this.platforms = resp.response.data.filter(
          (p) => !!p.knowledgebase?.notes_url,
        );
      }
      this.loading = false;
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
