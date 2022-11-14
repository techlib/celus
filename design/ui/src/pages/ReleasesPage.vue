<i18n lang="yaml">
en:
  header: Releases
  releases_unavailable: Unfortunately, information about releases is currently unavailable...
cs:
  header: Vydání
  releases_unavailable: Je nám líto, ale informace ohledně vydání jsou momentálně nedostupné...
</i18n>

<template>
  <v-container fluid>
    <v-row>
      <v-col>
        <h2 v-text="$t('header')"></h2>
      </v-col>
    </v-row>
    <v-row>
      <v-layout column>
        <v-flex>
          <v-col v-if="releases === null"> <LargeSpinner /></v-col>
          <v-col v-else-if="releases.length === 0">
            <p>{{ $t("releases_unavailable") }}</p></v-col
          >
          <v-col v-else>
            <ReleaseCard
              v-for="release in releases"
              :release="release"
              :key="release.version"
          /></v-col>
        </v-flex>
      </v-layout>
    </v-row>
  </v-container>
</template>

<script>
import ReleaseCard from "@/components/ReleaseCard";
import LargeSpinner from "@/components/util/LargeSpinner";
import axios from "axios";
import { mapActions } from "vuex";
export default {
  name: "ReleasesPage",
  components: {
    ReleaseCard,
    LargeSpinner,
  },

  data() {
    return {
      releases: null,
    };
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
      dismissLastRelease: "dismissLastRelease",
    }),
    async fetchReleases() {
      try {
        let response = await axios.get("/api/releases/");
        this.releases = response.data;
      } catch (error) {
        this.showSnackbar({
          content: "Error loading releases: " + error,
          color: "error",
        });
      }
    },
  },
  mounted() {
    this.fetchReleases();
    this.dismissLastRelease(true);
  },
};
</script>

<style scoped></style>
