<i18n lang="yaml" src="@/locales/sources.yaml"></i18n>
<i18n lang="yaml">
en:
  select_platform: Select platform
  continue: Continue

cs:
  select_platform: Vyberte platformu
  continue: Dále
</i18n>

<template>
  <v-card>
    <v-card-title>{{ $t("select_platform") }}</v-card-title>
    <v-card-text>
      <v-autocomplete
        :items="availablePlatforms"
        item-value="pk"
        item-text="name"
        :label="$t('select_platform')"
        v-model="platformId"
        :loading="loading"
      >
        <template v-slot:item="{ item }">
          <v-tooltip bottom max-width="600px" v-if="badge(item)">
            <template #activator="{ on }">
              <span>{{ item.name }}</span>
              <v-badge
                inline
                :content="$t(badge(item).content)"
                :color="badge(item).color"
              >
                <template v-slot:badge>
                  <span v-on="on">{{ $t(badge(item).content) }}</span>
                </template>
              </v-badge>
            </template>
            <span>{{ $t(badge(item).tooltip) }}</span>
          </v-tooltip>
          <span v-else>
            {{ item.name }}
          </span>
        </template>
      </v-autocomplete>
    </v-card-text>
    <v-card-actions>
      <v-spacer></v-spacer>
      <v-btn
        :to="
          platformId
            ? {
                name: 'platform-upload-data',
                params: { platformId: platformId },
              }
            : {}
        "
        :disabled="platformId === null"
        color="primary"
        >{{ $t("continue") }}</v-btn
      >
      <slot name="actions"></slot>
    </v-card-actions>
  </v-card>
</template>
<script>
import axios from "axios";
import { mapActions, mapState } from "vuex";
import { badge } from "@/libs/sources.js";

export default {
  name: "PlatformSelectionWidget",
  data() {
    return {
      platformId: null,
      platforms: [],
      loading: false,
    };
  },

  computed: {
    ...mapState({
      selectedOrganizationId: "selectedOrganizationId",
    }),
    availablePlatforms() {
      return this.platforms.sort((a, b) =>
        a.name ? a.name.localeCompare(b.name) : -1
      );
    },
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    async loadPlatforms() {
      try {
        this.loading = true;
        let response = await axios.get(
          `/api/organization/${this.selectedOrganizationId}/all-platform/`
        );
        this.platforms = response.data;
        // make sure platform name is not blank - use short_name if needed
        this.platforms.forEach((item) => {
          if (!item.name) item.name = item.short_name;
        });
      } catch (error) {
        this.showSnackbar({ content: "Error loading platform list: " + error });
      } finally {
        this.loading = false;
      }
    },
    badge(item) {
      return badge(item);
    },
  },
  mounted() {
    this.loadPlatforms();
  },
};
</script>
