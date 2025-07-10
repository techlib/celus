<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml">
en:
  intro: |
    Hierarchy of report types used to calculate each type of interest. Report types are sorted from the most preferred to the least preferred.
    When a report type is not available, the report type(s) on the right of it are used.
  intro_2: Reports which are not part of the hierarchy (do not have a replacement) are not shown here. They are always used when available and missing when not.
  next_report_type: "When '{name}' is not available, use the report type(s) on the right"
  no_report_types_to_show: No report types to show. This type of interest probably uses just individual report types without any hierarchy.
cs:
  intro: |
    Hierarchie reportů použitých k výpočtu jednotlivých typů zájmu. Reporty jsou seřazeny od nejpreferovanějších po nejméně preferované.
    Pokud není report k dispozici, použijí se reporty vpravo od něj.
  intro_2: Reporty, které nejsou součástí hierarchie (nemají náhradu) zde nejsou zobrazeny. Pokud jsou k dispozici, jsou vždy použity, pokud ne, chybí.
  next_report_type: "Když '{name}' není k dispozici, použijí se reporty na pravé straně"
  no_report_types_to_show: Žádné reporty k zobrazení. Tento typ zájmu pravděpodobně používá pouze individuální reporty bez hierarchie.
</i18n>

<template>
  <v-skeleton-loader v-if="loading" type="card, card, card, card, card, card" />
  <div v-else>
    <div class="mb-4">{{ $t("intro") }}</div>
    <div>{{ $t("intro_2") }}</div>
    <v-card
      v-for="ig in interestGroups"
      :key="ig.pk"
      class="mb-4"
      elevation="0"
    >
      <v-card-title>{{ ig.name }}</v-card-title>
      <v-card-text class="d-flex flex-row flex-wrap ga-4 align-center">
        <template v-for="(rts, index) in ig.report_type_groups" :key="index">
          <v-card>
            <v-card-text>
              <div v-for="rt in rts" :key="rt.pk">
                {{ rt.name }}
              </div>
            </v-card-text>
          </v-card>
          <v-tooltip
            v-if="index < ig.report_type_groups.length - 1"
            location="bottom"
          >
            <template #activator="{ props }">
              <v-icon v-bind="props">fas fa-arrow-right</v-icon>
            </template>
            <span>{{ $t("next_report_type", { name: rts[0].name }) }}</span>
          </v-tooltip>
        </template>
        <div v-if="ig.report_type_groups.length === 0">
          <span>{{ $t("no_report_types_to_show") }}</span>
        </div>
      </v-card-text>
    </v-card>
  </div>
</template>

<script>
import cancellation from "@/mixins/cancellation";

export default {
  name: "InterestOverviewHierarchy",

  mixins: [cancellation],

  data() {
    return {
      loading: false,
      interestGroups: [],
    };
  },

  methods: {
    async fetchInterestGroups() {
      this.loading = true;
      const { response, error } = await this.http({
        url: "/api/interest-groups/",
        method: "GET",
      });
      if (!error) {
        this.interestGroups = response.data;
        for (const ig of this.interestGroups) {
          await this.fetchInterestGroupDefinitions(ig);
        }
      }
      this.loading = false;
    },

    async fetchInterestGroupDefinitions(ig) {
      const { response, error } = await this.http({
        url: `/api/interest-groups/${ig.pk}/definitions/`,
        method: "GET",
      });
      if (!error) {
        ig.report_type_groups = this.sortAndGroupReportTypes(
          response.data.report_types,
        );
      }
    },

    sortAndGroupReportTypes(reportTypes) {
      let out = []; // array of arrays
      let head = reportTypes.filter((rt) => rt.superseded_by === null);
      while (head.length > 0) {
        out.push(head);
        head = reportTypes.filter((rt) =>
          head.some((h) => h.pk === rt.superseded_by),
        );
      }
      return out;
    },
  },

  mounted() {
    this.fetchInterestGroups();
  },
};
</script>
