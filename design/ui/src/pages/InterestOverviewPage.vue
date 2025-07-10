<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<i18n lang="yaml">
en:
  report_to_metrics: Report Metrics
  interest_metrics_intro: |
    The following table shows metrics assigned to individual reports which define the interest
    for that particular report. If a report does not have a metric assigned, no interest will
    be computed from the underlying data.
  interest_metrics_intro2: |
    Metrics are assigned to different interest groups/types. These define for which type of interest
    a metric will be used.
  hierarchy_visualization: Report Hierarchy
  hierarchy_visualization_intro: |
    Explore the complex relationships between report types and how interest computation flows through the system.
    This interactive visualization shows the hierarchy of report types, their superseding relationships, and the
    associated interest definitions and dimension mappings.
  hierarchy_visualization_intro2: |
    Click the button below to open the interactive hierarchy visualization in a new page.
  open_hierarchy_visualization: Open Hierarchy Visualization
  hierarchy_visualization_note: |
    The visualization provides an interactive tree diagram showing how report types relate to each other,
    which ones have interest definitions, and how dimension mappings work across the hierarchy.

cs:
  report_to_metrics: Metriky reportů
  interest_metrics_intro: |
    Následující tabulka ukazuje metriky přiřazené k jednotlivým reportům, které definují zájem
    pro daný report. Pokud nemá report vybranou žádnou metriku, nebude pro něj vypočítáván zájem.
  interest_metrics_intro2: |
    Metriky mohou být přiřazeny k různým skupinám/typům zájmu. Ty definují pro jaký typ zájmu budou
    data z dané metriky započítána.
  hierarchy_visualization: Vizualizace hierarchie
  hierarchy_visualization_intro: |
    Prozkoumejte složité vztahy mezi typy reportů a jak tok výpočtu zájmu prochází systémem.
    Tato interaktivní vizualizace ukazuje hierarchii typů reportů, jejich nahrazující vztahy a
    související definice zájmu a mapování dimenzí.
  hierarchy_visualization_intro2: |
    Klikněte na tlačítko níže pro otevření interaktivní vizualizace hierarchie na nové stránce.
  open_hierarchy_visualization: Otevřít vizualizaci hierarchie
  hierarchy_visualization_note: |
    Vizualizace poskytuje interaktivní stromový diagram ukazující, jak se typy reportů vztahují k sobě,
    které mají definice zájmu a jak funguje mapování dimenzí napříč hierarchií.
</i18n>

<template>
  <v-container fluid>
    <v-row>
      <v-col class="pb-0">
        <h2>{{ $t("pages.interest_overview") }}</h2>
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <v-card>
          <v-tabs
            v-model="tab"
            dark
            bg-color="info"
            centered
            align-tabs="center"
            slider-color="#ffffff33"
            slider-size="48"
          >
            <v-tab
              :class="{
                'tab-active': tab === 'hierarchy',
                'tab-inactive': tab !== 'hierarchy',
              }"
              value="hierarchy"
              >{{ $t("hierarchy_visualization") }}</v-tab
            >
            <v-tab
              :class="{
                'tab-active': tab === 'metrics',
                'tab-inactive': tab !== 'metrics',
              }"
              value="metrics"
              >{{ $t("report_to_metrics") }}</v-tab
            >
          </v-tabs>
          <v-card-text class="pa-8">
            <v-window v-model="tab">
              <v-window-item value="metrics">
                <v-card flat>
                  <v-card-text>
                    <p>{{ $t("interest_metrics_intro") }}</p>
                    <p class="pb-8 pt-4">{{ $t("interest_metrics_intro2") }}</p>
                    <InterestOverviewMetrics></InterestOverviewMetrics>
                  </v-card-text>
                </v-card>
              </v-window-item>
              <v-window-item value="hierarchy">
                <v-card flat>
                  <v-card-text>
                    <InterestOverviewHierarchy></InterestOverviewHierarchy>
                  </v-card-text>
                </v-card>
              </v-window-item>
            </v-window>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import InterestOverviewHierarchy from "@/components/InterestOverviewHierarchy";
import InterestOverviewMetrics from "@/components/InterestOverviewMetrics";

export default {
  name: "InterestOverview",

  components: { InterestOverviewMetrics, InterestOverviewHierarchy },

  data() {
    return {
      tab: "hierarchy",
    };
  },
};
</script>

<style scoped></style>
