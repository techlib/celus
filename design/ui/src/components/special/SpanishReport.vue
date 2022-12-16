<template>
  <div class="pt-8">
    <v-expansion-panels>
      <SpanishReportLine
        v-for="(definition, index) in resolvedDefinitions"
        :name="definition.name"
        :description="definition.description"
        :mainReportDefinition="definition.mainReportDefinition"
        :fallbackReportDefinition="definition.fallbackReportDefinition"
        :subtractFallbackReportDefinition="
          definition.subtractFallbackReportDefinition
        "
        :key="definition.name"
      />
    </v-expansion-panels>
  </div>
</template>

<script>
import SpanishReportLine from "@/components/special/SpanishReportLine";
import cancellation from "@/mixins/cancellation";
import cloneDeep from "lodash/cloneDeep";

export default {
  name: "SpanishReport",

  mixins: [cancellation],

  components: { SpanishReportLine },

  data() {
    return {
      reportDefinitions: [
        {
          name: "NCONSULRECPAGOCOUNT",
          description:
            "6.5.1.1.Búsquedas en recursos electrónicos de pago o con licencia a lo largo del " +
            "año:datos Counter.",
          mainReportDefinition: {
            reportType: "PR",
            metric: "Searches_Platform",
            filters: {
              Access_Method: "Regular",
            },
          },
          fallbackReportDefinition: {
            reportType: "DB1",
            metric: "Regular Searches",
          },
        },
        {
          name: "NVISDESREVCOUNTPAG",
          description:
            "6.5.2.1.1.1. Vistas y descargas del texto completo de artículos de revistas de " +
            "pago: datos Counter",
          mainReportDefinition: {
            reportType: "TR",
            metric: "Unique_Item_Requests",
            filters: {
              Access_Method: "Regular",
              Data_Type: "Journal",
              Access_Type: "Controlled",
            },
          },
          fallbackReportDefinition: {
            reportType: "JR1",
            metric: "FT Article Requests",
          },
          subtractFallbackReportDefinition: {
            reportType: "JR1GOA",
            metric: "FT Article Requests",
          },
        },
        {
          name: "NVISDESREVCOUNTOP",
          description:
            "6.5.2.1.1.2. Vistas y descargas del texto completo de artículos de revistas de " +
            "open access: datos Counter",
          mainReportDefinition: {
            reportType: "TR",
            metric: "Unique_Item_Requests",
            filters: {
              Access_Method: "Regular",
              Data_Type: "Journal",
              Access_Type: "OA_Gold",
            },
          },
          fallbackReportDefinition: {
            reportType: "JR1GOA",
            metric: "FT Article Requests",
          },
        },
        {
          name: "NVISDESLIBRCOUNTPAG",
          description:
            "6.5.2.1.2.1. Vistas y descargas del texto completo de libros de " +
            "pago: datos Counter",
          mainReportDefinition: {
            reportType: "TR",
            metric: "Unique_Title_Requests",
            filters: {
              Access_Method: "Regular",
              Data_Type: "Book",
              Access_Type: "Controlled",
            },
          },
          fallbackReportDefinition: {
            reportType: "BR1",
            metric: "Book Title Requests",
          },
        },
        {
          name: "NVISDESLIBRCOUNTOP",
          description:
            "6.5.2.1.2.2. Vistas y descargas del texto completo de libros open " +
            "access: datos Counter",
          mainReportDefinition: {
            reportType: "TR",
            metric: "Unique_Title_Requests",
            filters: {
              Access_Method: "Regular",
              Data_Type: "Book",
              Access_Type: "OA_Gold",
            },
          },
        },
        {
          name: "NVISDESDISTCOUNT",
          description:
            "6.5.2.1.3. Vistas y descargas del texto completo de tipologías de " +
            "datos (Data type) distintas de libros y revistas: datos Counter",
          mainReportDefinition: {
            reportType: "TR",
            metric: "Unique_Item_Requests",
            filters: {
              Data_Type: [
                "Article",
                "Book Segment",
                "Conferences",
                "Database",
                "Dataset",
                "Multimedia",
                "Newspaper or Newsletter",
                "Platform",
                "Other",
                "Repository Item",
                "Report",
                "Standards",
                "Thesis or Dissertation",
              ],
            },
          },
          fallbackReportDefinition: {
            reportType: "MR1",
            metric: null,
          },
        },
      ],
      reportTypes: {},
      accessMethods: [],
      dataTypes: [],
      accessTypes: [],
    };
  },

  computed: {
    resolvedDefinitions() {
      if (Object.keys(this.reportTypes).length === 0) {
        return [];
      }
      return this.reportDefinitions.map((definition) => {
        let def = cloneDeep(definition);
        def.mainReportDefinition.reportType =
          this.reportTypes[def.mainReportDefinition.reportType];
        if (def.fallbackReportDefinition) {
          def.fallbackReportDefinition.reportType =
            this.reportTypes[def.fallbackReportDefinition.reportType];
        }
        if (def.subtractFallbackReportDefinition) {
          def.subtractFallbackReportDefinition.reportType =
            this.reportTypes[def.subtractFallbackReportDefinition.reportType];
        }
        return def;
      });
    },
  },

  methods: {
    async loadReportTypes() {
      let result = await this.http({ url: "/api/report-type/" });
      this.reportTypes = {};
      result.response.data
        .filter((reportType) => reportType.short_name)
        .forEach((reportType) => {
          this.reportTypes[reportType.short_name] = reportType;
        });
    },
  },

  mounted() {
    this.loadReportTypes();
  },
};
</script>

<style lang="scss">
.spanish-report-line {
  border: solid 3px darkblue;
  display: flex;
  justify-content: space-between;
  align-items: baseline;

  * {
    margin: 1rem;
  }

  .report-type {
  }
  .name {
    font-weight: 300;
  }
  .description {
    font-weight: normal;
  }
  .total-value {
  }
}
</style>
