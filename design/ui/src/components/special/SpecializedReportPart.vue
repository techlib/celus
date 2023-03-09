<i18n lang="yaml" src="@/locales/common.yaml" />
<i18n lang="yaml">
en:
  main_report: Main Report
  fallback_report: Fallback Report
  no_data: This is just a report structure preview. To load the actual data, use the button at the top.

cs:
  main_report: Hlavní report
  fallback_report: Záložní report
  no_data: Data ještě nebyla načtena. Použijte tlačítko nahoře pro jejich načtení.
</i18n>

<template>
  <v-expansion-panel>
    <v-expansion-panel-header class="justify-space-between">
      <h3 class="name flex-grow-0">
        {{ name }}
        <v-tooltip bottom v-if="implementationNote" max-width="640px">
          <template #activator="{ on }">
            <v-icon color="info" small v-on="on">fa fa-info-circle</v-icon>
          </template>
          <span>{{ implementationNote }}</span>
        </v-tooltip>
      </h3>
      <h4 class="description">{{ description }}</h4>
      <h2 class="total-value flex-grow-0 me-4">
        <v-progress-circular v-if="loading" indeterminate />
        <span v-else-if="allReady">{{ formatInteger(total) }}</span>
        <span v-else>-</span>
      </h2>
    </v-expansion-panel-header>
    <v-expansion-panel-content>
      <v-sheet>
        <p v-if="explanation" class="explanation font-weight-light">
          {{ explanation }}
        </p>
        <table class="overview" v-if="lastStage">
          <tr v-for="sourceId in lastStage.usedDataSources" :key="sourceId">
            <th>
              {{
                reportDataSources[sourceId].fallbackFor
                  ? $t("fallback_report")
                  : $t("report")
              }}
            </th>
            <td class="pe-2">
              {{ reportDataSources[sourceId].name }}
            </td>
            <td>
              <ReportPartParams :definition="reportDataSources[sourceId]" />
            </td>
          </tr>
        </table>
        <v-checkbox
          v-model="nonZeroOnly"
          label="Non-zero rows only"
          v-if="allReady"
        />
      </v-sheet>
      <v-tabs v-model="selectedStage" v-if="stages.length > 1 && allReady">
        <v-tab
          v-for="(stage, index) in stages"
          :key="stage.name"
          :value="index"
        >
          {{ stage.name }}
        </v-tab>
      </v-tabs>
      <p class="note pt-6" v-if="!allReady">
        {{ $t("no_data") }}
      </p>
      <v-data-table
        v-else-if="
          showDetail && selectedStageData && selectedStageData.length > 0
        "
        :items="formattedData"
        item-key="pk"
        :headers="tableColumns"
        sort-by="total"
        sort-desc
      >
        <template #item.total="{ item }">
          {{ formatInteger(item.total) }}
        </template>
      </v-data-table>
    </v-expansion-panel-content>
  </v-expansion-panel>
</template>
<script>
import cancellation from "@/mixins/cancellation";
import { mapGetters } from "vuex";
import { formatInteger } from "@/libs/numbers";
import cloneDeep from "lodash/cloneDeep";
import ReportPartParams from "@/components/special/ReportPartParams";

export default {
  name: "SpecializedReportPart",
  components: { ReportPartParams },
  mixins: [cancellation],

  props: {
    name: {
      type: String,
      required: false,
    },
    description: {
      type: String,
      required: false,
    },
    explanation: {
      type: String,
      required: false,
    },
    stages: {
      type: Array,
      required: true,
    },
    implementationNote: {
      type: String,
      required: false,
    },
    data: {
      type: Object,
      required: false,
    },
    reportDataSources: {
      type: Object,
      required: false,
    },
    loading: {
      type: Boolean,
      required: false,
    },
  },

  data() {
    return {
      showDetail: true,
      nonZeroOnly: true,
      selectedStage: this.stages.length - 1,
    };
  },

  computed: {
    ...mapGetters({
      dateRangeStart: "dateRangeStartText",
      dateRangeEnd: "dateRangeExplicitEndText",
      organizationObj: "selectedOrganization",
    }),
    allReady() {
      return this.data.stages?.length > 0;
    },
    organization() {
      return this.organizationObj.pk !== -1 ? this.organizationObj.pk : null;
    },
    dateRange() {
      if (this.selectedStageData && this.selectedStageData.length > 0) {
        return Object.keys(this.selectedStageData[0].monthly_data);
      }
      return [];
    },
    tableColumns() {
      return [
        {
          text: this.$t("labels.platform"),
          value: "primary_obj",
          align: "left",
          sortable: true,
        },
        {
          text: this.$t("labels.source"),
          value: "source_name",
          sortable: true,
        },
        {
          text: this.$t("labels.total"),
          value: "total",
          align: "right",
          sortable: true,
        },
        ...this.dateRange.map((date) => {
          return {
            text: date,
            value: `monthly_data.${date}`,
            align: "right",
            sortable: true,
            cellClass: "font-weight-light",
          };
        }),
      ];
    },
    selectedStageData() {
      if (this.allReady) return this.data.stages[this.selectedStage].data;
      return [];
    },
    lastStageData() {
      if (this.allReady) return this.data.stages[this.stages.length - 1].data;
      return [];
    },
    lastStage() {
      if (this.stages) return this.stages[this.stages.length - 1];
      return null;
    },
    finalData() {
      if (this.nonZeroOnly) {
        return this.selectedStageData.filter((r) => r.total > 0);
      }
      return this.selectedStageData;
    },
    formattedData() {
      let data = cloneDeep(this.finalData);
      data.forEach((r) => {
        this.dateRange.forEach((date) => {
          r.monthly_data[date] = formatInteger(r.monthly_data[date]);
        });
      });
      return data;
    },
    total() {
      return this.lastStageData.reduce((ac, rec) => ac + rec.total, 0);
    },
  },

  methods: {
    formatInteger,
  },
};
</script>

<style lang="scss" scoped>
.description {
  font-weight: normal;
}
.name {
  min-width: 16rem;
  margin-right: 1.5rem;
}
.total-value {
  &.trouble {
    font-size: 1rem;
    font-weight: normal;
    font-style: italic;
  }
}
.note {
  padding-left: 2px;
  font-style: italic;
  font-size: 0.8rem;
  color: #666;
}
.explanation {
  font-size: 0.875rem;
  border-left: solid 4px #75ccff; //#4db6ac;
  padding: 1rem 0 1rem 1rem;
}
</style>
