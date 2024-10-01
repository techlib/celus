<i18n src="@/locales/common.yaml" lang="yaml"></i18n>
<i18n lang="yaml">
en:
  knowledgebase_article: Detailed information about the format from Celus knowledgebase

cs:
  knowledgebase_article: Podrobné informace o formátu ve znalostní bázi Celus
</i18n>

<template>
  <v-data-table
    :items="platforms"
    item-key="pk"
    :headers="headers"
    sort-by="name"
    :items-per-page="-1"
    :search="search"
    :loading="loading"
    class="auto-table"
    dense
  >
    <template #item.actions="{ item }">
      <v-tooltip bottom>
        <template #activator="{ on }">
          <v-btn
            v-on="on"
            text
            :to="{
              name: 'platform-upload-data',
              params: { platformId: item.pk },
              query: { method: 'raw' },
            }"
            color="secondary"
            small
          >
            <v-icon small class="pr-2">fa-upload</v-icon>
            {{ $t("actions.upload_data") }}
          </v-btn>
        </template>
        {{ $t("actions.upload_data") }}
      </v-tooltip>
    </template>

    <template #item.info="{ item }">
      <v-tooltip bottom max-width="600px">
        <template #activator="{ on }">
          <v-btn
            v-if="item.knowledgebase && item.knowledgebase.notes_url"
            v-on="on"
            :href="item.knowledgebase.notes_url"
            target="_blank"
            text
            small
            color="tertiary"
          >
            <v-icon small color="info" class="pr-2">fa-info-circle</v-icon>
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
            clear-icon="fa-times"
            append-icon="fa-search"
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
        { text: this.$t("title_fields.short_name"), value: "short_name" },
        { text: this.$t("title_fields.name"), value: "name" },
        { text: this.$t("title_fields.knowledgebase"), value: "info" },
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
        this.platforms = resp.response.data.filter(
          (p) => !!p.knowledgebase?.notes_url
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
