<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

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
    <v-expansion-panel-title class="justify-space-between">
      <h3 class="name flex-grow-0">
        {{ name }}
        <v-tooltip
          location="bottom"
          v-if="implementationNote"
          max-width="640px"
        >
          <template #activator="{ props }">
            <v-icon color="info" size="small" v-bind="props"
              >fa fa-info-circle</v-icon
            >
          </template>
          <span>{{ implementationNote }}</span>
        </v-tooltip>
      </h3>
      <h4 class="description">{{ description }}</h4>
      <h2 class="total-value flex-grow-0 me-4 text-right">
        <v-progress-circular v-if="loading" indeterminate></v-progress-circular>
        <span v-else-if="allReady">{{ formatInteger(total) }}</span>
        <span v-else>-</span>
      </h2>
    </v-expansion-panel-title>
    <v-expansion-panel-text>
      <v-sheet>
        <p v-if="explanation" class="explanation font-weight-light mb-4">
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
              <ReportPartParams
                :definition="reportDataSources[sourceId]"
              ></ReportPartParams>
            </td>
          </tr>
        </table>
        <v-checkbox
          v-model="nonZeroOnly"
          label="Non-zero rows only"
          v-if="allReady"
          color="primary"
        ></v-checkbox>
      </v-sheet>
      <v-tabs
        v-model="selectedStage"
        v-if="stages.length > 1 && allReady"
        color="#2d5854"
      >
        <v-tab
          v-for="(stage, index) in stages"
          :key="stage.name"
          :model-value="index"
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
        v-model:sort-by="orderBy"
        sort-desc
        class="main_table"
        density="default"
      >
        <template #item.total="{ item }">
          <span class="item_total">
            {{ formatInteger(item.total) }}
          </span>
        </template>
        <template #item.source_name="{ item }">
          <span :style="{ color: sourceColor(item.source_name) }">{{
            item.source_name
          }}</span>
        </template>
      </v-data-table>
    </v-expansion-panel-text>
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
      palette: ["#000000", "#9C27B0", "#4CAF50", "#3F51B5", "#E91E63"],
      orderBy: [{ key: "total", order: "asc" }],
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
          title: this.$t("labels.platform"),
          value: "primary_obj",
          align: "start",
          sortable: true,
        },
        {
          title: this.$t("labels.source"),
          value: "source_name",
          sortable: true,
        },
        {
          title: this.$t("labels.total"),
          value: "total",
          align: "end",
          sortable: true,
        },
        ...this.dateRange.map((date) => {
          return {
            title: date,
            value: `monthly_data.${date}`,
            align: "end",
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
    sourcesInLastStage() {
      let counter = new Map();
      this.lastStageData.forEach((r) => {
        const value = r.total > 0 ? 1 : 0; // only count sources with non-zero total
        if (counter.has(r.source_name))
          counter.set(r.source_name, counter.get(r.source_name) + value);
        else counter.set(r.source_name, value);
      });
      let countSource = [];
      counter.forEach((v, k) => {
        countSource.push({ source: k, count: v });
      });
      countSource.sort((a, b) => b.count >= a.count);
      return countSource.map((r) => r.source);
    },
  },

  methods: {
    formatInteger,
    sourceColor(source) {
      return this.palette[
        this.sourcesInLastStage.indexOf(source) % this.palette.length
      ];
    },
  },
};
</script>

<style lang="scss" scoped>
.description {
  font-weight: normal;
  flex: 1;
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

.main_table {
  color: grey;
  &:deep(th:nth-child(3)) {
    color: black;
    font-weight: 600;
    letter-spacing: 0.2px;
  }
  .item_total {
    color: black;
    font-weight: 600;
    letter-spacing: 0.2px;
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
