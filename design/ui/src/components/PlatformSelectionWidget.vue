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
      >
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
export default {
  name: "PlatformSelectionWidget",
  data() {
    return {
      platformId: null,
      platforms: [],
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
        let response = await axios.get(
          `/api/organization/${this.selectedOrganizationId}/all-platform/`
        );
        this.platforms = response.data;
      } catch (error) {
        this.showSnackbar({ content: "Error loading platform list: " + error });
      }
    },
  },
  mounted() {
    this.loadPlatforms();
  },
};
</script>
