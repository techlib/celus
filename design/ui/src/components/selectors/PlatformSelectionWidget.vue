<i18n lang="yaml" src="@/locales/sources.yaml"></i18n>
<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml" src="@/locales/dialog.yaml"></i18n>

<template>
  <v-card>
    <!-- Submit on enter can't be used here because it is not compatible with v-autocomplete. -->
    <v-card-title>{{ $t("title_fields.select_platform") }}</v-card-title>
    <v-card-text>
      <PlatformSelector
        :platforms="availablePlatforms"
        v-model="platformId"
        :loading="loading"
      />
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
import PlatformSelector from "@/components/selectors/PlatformSelector.vue";

export default {
  name: "PlatformSelectionWidget",
  components: { PlatformSelector },
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
