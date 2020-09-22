<i18n lang="yaml" src="../locales/pub-types.yaml"></i18n>

<i18n lang="yaml">
en:
  titles_with_most_interest: Highest interest of this type
  no_matching_titles: Nothing with this type of interest

cs:
  titles_with_most_interest: Největší zájem tohoto typu
  no_matching_titles: Pro tento typ zájmu nejsou žádné záznamy
</i18n>

<template>
  <v-card min-height="320px" height="100%" min-width="400" class="text-center">
    <!-- publication type selector -->
    <div v-if="pubTypes && pubTypes.length" class="float-right mt-4 mr-3">
      <v-btn-toggle v-model="selectedPubType">
        <v-tooltip bottom v-for="pubType in pubTypes" :key="pubType.value">
          <template #activator="{ on }">
            <v-btn v-on="on" :value="pubType.value" small>
              <v-icon small>fa {{ pubType.icon }}</v-icon>
            </v-btn>
          </template>
          {{ $t(pubType.text) }}
        </v-tooltip>
      </v-btn-toggle>
    </div>

    <v-card-title v-text="interestGroup.name"></v-card-title>
    <v-card-subtitle class="text-left">{{
      $t("titles_with_most_interest")
    }}</v-card-subtitle>
    <v-card-text>
      <v-progress-linear v-if="titles && loading" indeterminate />
      <v-simple-table v-if="titles && titles.length" class="dashboard" dense>
        <tbody>
          <tr v-for="title in titles" :key="title.pk">
            <td class="text-left">
              <router-link
                :to="{
                  name: 'title-detail',
                  params: { platformId: null, titleId: title.pk },
                }"
              >
                {{ title.name }}
              </router-link>
            </td>
            <td class="text-right">
              {{ formatInteger(title.interests[interestGroup.short_name]) }}
            </td>
          </tr>
        </tbody>
      </v-simple-table>
      <div v-else-if="titles">
        <!-- titles loaded, but no data -->
        <div class="mt-8 mb-2">
          <v-icon large color="grey">fa-times</v-icon>
        </div>
        {{ $t("no_matching_titles") }}
      </div>
      <LargeSpinner v-else />
    </v-card-text>
  </v-card>
</template>
<script>
import LargeSpinner from "@/components/util/LargeSpinner";
import { formatInteger } from "@/libs/numbers";
import axios from "axios";
import { mapActions } from "vuex";

export default {
  name: "TopTenDashboardWidget",
  components: { LargeSpinner },
  props: {
    urlBase: { required: true, type: String },
    pubTypes: { default: () => [] },
    interestGroup: null,
  },

  data() {
    return {
      titles: null,
      selectedPubType: null,
      loading: false,
    };
  },

  computed: {
    url() {
      if (this.urlBase && this.interestGroup) {
        let url = this.urlBase + `&order_by=${this.interestGroup.short_name}`;
        if (this.selectedPubType) {
          url += `&pub_type=${this.selectedPubType}`;
        }
        return url;
      }
      return null;
    },
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    formatInteger,
    async fetchTitleInterest() {
      this.loading = true;
      //this.titles = null
      if (this.url) {
        try {
          let response = await axios.get(this.url);
          this.titles = response.data.filter(
            (item) => item.interests[this.interestGroup.short_name] > 0
          );
        } catch (error) {
          this.showSnackbar({
            content: "Error loading interesting titles: " + error,
            color: "error",
          });
        } finally {
          this.loading = false;
        }
      }
    },
  },

  watch: {
    url() {
      this.fetchTitleInterest();
    },
  },

  mounted() {
    this.fetchTitleInterest();
  },
};
</script>
