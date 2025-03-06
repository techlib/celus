<i18n lang="yaml" src="@/locales/pub-types.yaml"></i18n>

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
      <v-btn-toggle
        v-model="selectedPubType"
        variant="outlined"
        divided
        text-warning
        density="compact"
      >
        <v-tooltip
          location="bottom"
          v-for="pubType in pubTypes"
          :key="pubType.value"
        >
          <template #activator="{ props }">
            <v-btn
              v-bind="props"
              style="padding: 0 12px"
              size="small"
              :value="pubType.value"
            >
              <v-icon size="small">fa {{ pubType.icon }}</v-icon>
            </v-btn>
          </template>
          {{ $t(pubType.text) }}
        </v-tooltip>
      </v-btn-toggle>
    </div>
    <v-card-title class="text-left">{{ interestGroup.name }}</v-card-title>
    <v-card-subtitle class="text-left">{{
      $t("titles_with_most_interest")
    }}</v-card-subtitle>
    <v-card-text>
      <LargeSpinner v-if="loading"></LargeSpinner>
      <v-progress-linear v-else-if="!titles" indeterminate></v-progress-linear>
      <v-table
        v-if="titles && titles.length"
        class="dashboard"
        density="compact"
      >
        <tbody>
          <tr v-for="title in titles" :key="title.pk">
            <td class="text-left">
              <router-link
                :to="{
                  name: 'title-detail',
                  params: { platformId: null, titleId: title.pk },
                }"
              >
                <ShortenText :text="title.name" :length="40"></ShortenText>
              </router-link>
            </td>
            <td class="text-right">
              {{ formatInteger(title.interests[interestGroup.short_name]) }}
            </td>
          </tr>
        </tbody>
      </v-table>
      <div v-else-if="titles">
        <!-- titles loaded, but no data -->
        <div class="mt-8 mb-2">
          <v-icon color="grey" size="large">fa fa-times</v-icon>
        </div>
        {{ $t("no_matching_titles") }}
      </div>
    </v-card-text>
  </v-card>
</template>

<script>
import LargeSpinner from "@/components/util/LargeSpinner";
import ShortenText from "@/components/ShortenText";
import { formatInteger } from "@/libs/numbers";
import cancellation from "@/mixins/cancellation";

export default {
  name: "TopTenDashboardWidget",
  mixins: [cancellation],
  components: { ShortenText, LargeSpinner },
  props: {
    requestBase: { required: true, type: Object },
    interestGroup: { required: true, type: Object },
    pubTypes: { default: () => [] },
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
      let { url, params } = this.requestBase;
      params = {
        ...params,
        order_by: this.interestGroup.short_name,
        ...(this.selectedPubType && { pub_type: this.selectedPubType }),
      };
      return this.$router.resolve({ path: url, query: params }).href;
    },
  },

  methods: {
    formatInteger,

    async fetchTitleInterest() {
      this.titles = null;
      if (!this.requestBase || !this.interestGroup) return;

      this.loading = true;
      const { response } = await this.http({
        url: this.url,
        label: this.interestGroup.name,
      });
      this.loading = false;

      const group = this.interestGroup.short_name;
      this.titles = response
        ? response.data.filter((item) => item.interests[group] > 0)
        : [];
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
