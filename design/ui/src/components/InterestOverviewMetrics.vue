<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<i18n lang="yaml">
en:
  labels:
    reports: Reports
    report_types: Report types
    metrics: Metrics
    target_metrics: Target metrics
    interest_type: Interest type
    record_count: Record count
    all: All reports
    undefined: Without metric
    interest_group_filter: Interest type filter
    source_metric: Source metric
    interest_metric: Interest metric
    used_by_platforms: Used by platforms
    no_metric: No metric is assigned as defining interest
  tt:
    record_count: Please note that the number of records may be up to one day old
    interest_metric: |
      Metric from source report may be remapped to a different metric name in
      interest. Such cases are marked by italic font.

cs:
  labels:
    reports: Reporty
    report_types: Typy reportů
    metrics: Metriky
    target_metrics: Cílové metriky
    interest_type: Typ zájmu
    record_count: Počet záznamů
    all: Všechny reporty
    undefined: Bez definované metriky
    interest_group_filter: Filtr typu zájmu
    source_metric: Zdrojová metrika
    interest_metric: Metrika zájmu
    used_by_platforms: Použit u platforem
    no_metric: Není přiřazena žádná metrika definující zájem
  tt:
    record_count: Počet záznamů je jen orientační - může být až jeden den starý
    interest_metric: |
      Metrika ze zdrojových dat může být v zájmu přemapována na jiné jméno. Tyto
      případy jsou zvýrazněny kurzívou.
</i18n>

<template>
  <v-data-table
    :items="visibleItems"
    item-key="pk"
    item-value="pk"
    density="default"
    :headers="headers"
    :loading="loading"
    :search="search"
    :expanded="expanded"
    expand-icon="fas fa-caret-down"
    :items-per-page="50"
    :items-per-page-options="[50, 100, -1]"
    :custom-filter="searchFilter"
    class="auto-table"
  >
    <template #top>
      <v-row>
        <v-col cols="auto">
          <v-select
            v-model="selectedGroup"
            :items="interestGroups"
            item-value="pk"
            style="min-width: 200px"
            item-title="name"
            :label="$t('labels.interest_group_filter')"
          >
            <template v-slot:item="{ item, props }">
              <v-list-item
                v-bind="props"
                title=""
                :class="item.raw.special ? 'font-italic' : ''"
              >
                {{ item.raw.name }}
              </v-list-item>
            </template>
          </v-select>
        </v-col>
        <v-spacer></v-spacer>
        <v-col cols="4">
          <v-text-field
            style="min-width: 85px"
            v-model="search"
            append-inner-icon="fa fa-search"
            :label="$t('labels.search')"
            single-line
            hide-details
            clearable
          >
          </v-text-field>
        </v-col>
      </v-row>
    </template>
    <template #item.data-table-expand="{ item }">
      <v-btn icon variant="text" size="small" @click="toggleExpand(item)">
        <v-icon>
          {{
            expanded.includes(item.pk) ? "fas fa-caret-up" : "fas fa-caret-down"
          }}
        </v-icon>
      </v-btn>
    </template>
    <template #expanded-row="{ columns, item }">
      <tr class="item_expanded_space">
        <td :colspan="columns.length" class="pa-2">
          <v-sheet class="pl-8">
            <v-table
              v-if="item.interest_metric_set.length > 0"
              class="ml-8 font-weight-light"
              density="compact"
            >
              <thead>
                <tr>
                  <th
                    v-text="$t('labels.interest_type')"
                    class="interest_type"
                  ></th>
                  <th
                    v-text="$t('labels.source_metric')"
                    class="source_metric"
                  ></th>
                  <th>
                    {{ $t("labels.interest_metric") }}
                    <v-tooltip location="bottom center">
                      <template #activator="{ props }">
                        <v-icon color="info" size="small" v-bind="props"
                          >fa fa-info-circle</v-icon
                        >
                      </template>
                      {{ $t("tt.interest_metric") }}
                    </v-tooltip>
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(metric, index) in item.interest_metric_set"
                  :key="index"
                  style="height: 32px"
                >
                  <td>{{ metric.interest_group.name }}</td>
                  <td>{{ metric.metric.short_name }}</td>
                  <td v-if="metric.target_metric" class="font-italic">
                    {{ metric.target_metric.name }}
                  </td>
                  <td v-else>
                    {{ metric.metric.short_name }}
                  </td>
                </tr>
              </tbody>
            </v-table>
            <div v-else class="pl-8">
              {{ $t("labels.no_metric") }}
            </div>
          </v-sheet>
        </td>
      </tr>
    </template>
    <template #item.short_name="{ item }">
      <ReportChip :report="item"></ReportChip>
    </template>
    <template #item.metrics="{ item }">
      <ReportInterestGroups
        :report="item"
        :highlight-group-id="selectedGroup"
        :max-count="3"
      ></ReportInterestGroups>
    </template>
    <template #item.approx_record_count="{ item }">
      <span class="text-caption">{{
        formatInteger(item.approx_record_count)
      }}</span>
    </template>
    <template #header.approx_record_count="{ column }">
      <v-tooltip location="bottom">
        <template #activator="{ props }">
          {{ column.title }}
          <v-icon
            size="small"
            color="info"
            v-bind="props"
            icon="fa fa-info-circle"
          >
          </v-icon>
        </template>
        {{ $t("tt.record_count") }}
      </v-tooltip>
    </template>
  </v-data-table>
</template>

<script>
import ReportChip from "@/components/reporting/ReportChip";
import cancellation from "@/mixins/cancellation";
import ReportInterestGroups from "@/components/ReportInterestGroups";
import { mapState } from "vuex";
import { formatInteger } from "@/libs/numbers";

export default {
  name: "InterestOverviewMetrics",

  mixins: [cancellation],

  components: { ReportInterestGroups, ReportChip },

  data() {
    return {
      items: [],
      expanded: [],
      search: "",
      loading: false,
      interestGroups: [],
      selectedGroup: null,
    };
  },

  computed: {
    ...mapState({
      lang: "appLanguage",
    }),
    headers() {
      return [
        {
          title: "",
          value: "data-table-expand",
          sortable: false,
          align: "start",
        },
        {
          title: this.$i18n.t("labels.report_types"),
          value: "short_name",
          key: "short_name",
        },
        {
          title: this.$i18n.t("labels.metrics"),
          value: "metrics",
          sortable: false,
        },
        {
          title: this.$i18n.t("labels.used_by_platforms"),
          value: "used_by_platforms",
          key: "used_by_platforms",
          align: "end",
          cellClass: "text-caption",
        },
        {
          title: this.$i18n.t("labels.record_count"),
          value: "approx_record_count",
          key: "approx_record_count",
          align: "end",
        },
      ];
    },
    visibleItems() {
      if (this.selectedGroup === -1) {
        return this.items.filter(
          (item) => item.interest_metric_set.length === 0,
        );
      }
      if (this.selectedGroup) {
        return this.items.filter((item) =>
          item.interest_metric_set.find(
            (im) => im.interest_group.pk === this.selectedGroup,
          ),
        );
      }
      return this.items;
    },
  },

  methods: {
    formatInteger,
    toggleExpand(item) {
      const index = this.expanded.indexOf(item.pk);
      if (index > -1) {
        this.expanded.splice(index, 1);
      } else {
        this.expanded.push(item.pk);
      }
    },
    async fetchReportData() {
      const url = "api/report-interest-metric/";
      this.loading = true;
      const { response } = await this.http({ url });
      this.loading = false;
      if (response) {
        this.items = response.data;
        this.items.sort((a, b) => a.short_name.localeCompare(b.short_name));
        let igMap = new Map();
        this.items.forEach((item) =>
          item.interest_metric_set.forEach((im) =>
            igMap.set(im.interest_group.pk, im.interest_group),
          ),
        );
        let igsSorted = [...igMap.values()];
        igsSorted.sort((a, b) => a.name.localeCompare(b.name));
        this.interestGroups = [
          {
            pk: null,
            name: this.$t("labels.all"),
            special: true,
          },
          {
            pk: -1,
            name: this.$t("labels.undefined"),
            special: true,
          },
          ...igsSorted,
        ];
      }
    },
    searchFilter(value, search, item) {
      // Search platform directly
      let match = (value, search) =>
        value && value.toString().toLowerCase().includes(search.toLowerCase());
      if (match(value, search)) {
        return true;
      }
      for (const im of item.raw.interest_metric_set) {
        if (match(im.metric.short_name, search)) {
          return true;
        }
        if (match(im.metric[`name_${this.lang}`], search)) {
          return true;
        }
        if (!!im.target_metric && match(im.target_metric.short_name, search)) {
          return true;
        }
        if (
          !!im.target_metric &&
          match(im.target_metric[`name_${this.lang}`], search)
        ) {
          return true;
        }
        if (!!im.interest_group && match(im.interest_group.name, search)) {
          return true;
        }
      }
      return false;
    },
  },
  mounted() {
    this.fetchReportData();
  },
};
</script>

<style lang="scss" scoped>
.interest_type {
  width: 10%;
}
.source_metric {
  width: 20%;
}
</style>
