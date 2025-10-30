<i18n lang="yaml">
en:
  anomaly_report: Anomaly Report
  calculation_details: "Anomalies are reported when the usage in one month differs significantly from the usage pattern in the preceding 12 months. The measure of this deviation is expressed as <b>Significance</b>. For more information, see <a href='https://support.celus.net/support/solutions/articles/103000369561' target='_blank' rel='noopener noreferrer'>our knowledgebase article</a>."
  data_not_harvested: The data for previous month may still be incomplete.
  details: Details
  anomalies_found: |
    Anomalies (<strong>{count}</strong>) were found in the following platforms: <strong>{platforms}</strong>.
  anomalies_total_platforms: |
    Anomalies (<strong>{count}</strong>) were found on <strong>{platforms_count}</strong> platforms.
  no_anomalies_found: No anomalies were found for the selected time period.
  historical_values: Historical values
  median: Median
  significance: Significance
  low: Low
  medium: Medium
  high: High
  incorrect_months_warning: The start date must be before the end date.
  difference_from_median: Difference from Median
  anomaly_level: Anomaly Level
  open_in_reporting: Open in Reporting
  none_deviation: None of the values shows significant deviation.
  all_deviation: All of the values ({reasonsCount}/{dimCount}) show significant deviation.
  some_deviation: Some of the values ({reasonsCount}/{dimCount}) show significant deviation.
  one_deviation: There is only one {label} ({text}) in the data.
  12_month_median: Median (12 months)
cs:
  anomaly_report: Přehled anomálií
  calculation_details: "Anomálie jsou detekovány, pokud se využití v jednom měsíci významně liší od trendu v předchozích 12 měsících. Míra této odchylky je vyjádřena jako <b>Významnost</b>. Více informací naleznete v <a href='https://support.celus.net/support/solutions/articles/103000369561' target='_blank' rel='noopener noreferrer'>našem článku v knowledge base</a>."
  data_not_harvested: Data za předchozí měsíc mohou být stále neúplná.
  details: Podrobnosti
  anomalies_found: |
    Anomálie (<strong>{count}</strong>) byly nalezeny na platformách: <strong>{platforms}</strong>.
  anomalies_total_platforms: |
    Anomálie (<strong>{count}</strong>) byly nalezeny na <strong>{platforms_count}</strong> platformách.
  no_anomalies_found: Pro zadané časové období nebyly nalezeny žádné anomálie.
  historical_values: Historické hodnoty
  median: Medián
  significance: Významnost
  low: Nízká
  medium: Střední
  high: Vysoká
  incorrect_months_warning: Počáteční datum musí být před koncovým datem.
  difference_from_median: Rozdíl od mediánu
  anomaly_level: Úroveň anomálie
  open_in_reporting: Otevřít v Reportingu
  none_deviation: Žádná hodnota nevykazuje významnou odchylku.
  all_deviation: Všechny hodnoty ({reasonsCount}/{dimCount}) vykazují významnou odchylku.
  some_deviation: Některé hodnoty ({reasonsCount}/{dimCount}) vykazují významnou odchylku.
  one_deviation: V datech je pouze jedna {label} ({text}).
  12_month_median: Medián (12 měsíců)
</i18n>
<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<template>
  <v-container fluid class="px-4">
    <h2 class="mb-4">{{ t("anomaly_report") }}</h2>
    <p class="mb-2" v-html="t('calculation_details')"></p>
    <p class="mb-4" v-if="anomalyData?.length">
      <span
        v-if="platformsCount > 10"
        v-html="
          t('anomalies_total_platforms', {
            count: anomalyData.length,
            platforms_count: platformsCount,
          })
        "
      ></span>
      <span
        v-else
        v-html="
          t('anomalies_found', {
            count: anomalyData.length,
            platforms: platformSummary,
          })
        "
      ></span>
    </p>

    <v-row class="mt-4">
      <v-col cols="6" sm="4" md="3" lg="2">
        <DatePicker
          v-model="selectedDatePickerFrom"
          :max-date-limit="lastMonth"
          :min-date="minMonthDate"
          :label="t('title_fields.start_date')"
          :styleField="'min-width: 170px'"
        >
        </DatePicker>
      </v-col>
      <v-col cols="6" sm="4" md="3" lg="2">
        <DatePicker
          v-model="selectedDatePickerTo"
          :max-date-limit="lastMonth"
          :min-date="minMonthDate"
          :label="t('title_fields.end_date')"
          :styleField="'min-width: 170px'"
        >
        </DatePicker>
      </v-col>
      <v-spacer />
      <v-col cols="12" sm="6" md="4" lg="3">
        <PlatformSelector
          :platforms="anomalyPlatforms"
          v-model="selectedPlatform"
          :label="t('platform')"
          :return-object="true"
        ></PlatformSelector>
      </v-col>
      <v-col cols="12" sm="6" md="4" lg="3">
        <v-select
          v-model="selectedReportType"
          :items="anomalyReportTypes"
          item-title="name"
          item-value="id"
          :label="t('labels.report_type')"
          :return-object="true"
          clearable
          clear-icon="fas fa-times"
        />
      </v-col>
    </v-row>
    <p v-if="selectedMonthFrom > selectedMonthTo" class="text-error">
      {{ t("incorrect_months_warning") }}
    </p>
    <p v-if="showHarvestWarning" class="text-error">
      {{ t("data_not_harvested") }}
    </p>

    <v-data-table
      v-if="filteredAnomalies"
      :headers="headers"
      :items="filteredAnomalies"
      class="elevation-1"
      item-key="id"
      item-value="id"
      v-model:expanded="expandedRows"
      v-model:sort-by="sortBy"
      expand-on-click
      :hide-default-footer="filteredAnomalies.length <= 10"
      show-expand
      :loading="loadingData"
    >
      <template v-slot:item.date="{ item }">
        {{ ymDateFormat(item.date) }}
      </template>

      <template v-slot:item.value="{ item }">
        <span class="font-weight-bold">{{ item.value.toLocaleString() }}</span>
      </template>

      <template v-slot:item.median="{ item }">
        {{ item.median.toLocaleString() }}
      </template>

      <template v-slot:item.differenceFromMedian="{ item }">
        <div class="d-inline-flex align-center">
          <span class="mr-1">
            {{ formatMedianDifference(item.differenceFromMedian) }}
          </span>
          <v-icon
            size="x-small"
            :color="diffColor(item.differenceFromMedian)"
            class="mr-1"
          >
            {{
              item.differenceFromMedian > 0
                ? "fa fa-arrow-up"
                : "fa fa-arrow-down"
            }}
          </v-icon>
          <v-sparkline
            :model-value="historyValues(item.history)"
            :line-width="5"
            :color="diffColor(item.differenceFromMedian)"
            :smooth="false"
            :fill="false"
            :padding="8"
            style="width: 60px; height: 16px"
          />
        </div>
      </template>

      <template v-slot:item.significance="{ item }">
        <v-tooltip location="top" :text="significanceLabel(item.significance)">
          <template #activator="{ props }">
            <span v-bind="props">{{ item.significance.toLocaleString() }}</span>
          </template>
        </v-tooltip>
      </template>

      <template v-slot:item.actions="{ item }">
        <v-tooltip location="top" :text="t('open_in_reporting')">
          <template #activator="{ props }">
            <v-btn
              v-bind="props"
              color="primary"
              variant="text"
              :to="flexiRoute(item)"
              target="_blank"
              @click.stop
              @mousedown.stop
              icon
              size="small"
            >
              <v-icon size="small">fa fa-arrow-up-from-bracket</v-icon>
            </v-btn>
          </template>
        </v-tooltip>
      </template>

      <template #no-data>
        {{ t("no_anomalies_found") }}
      </template>

      <template v-slot:expanded-row="{ columns, item }">
        <tr>
          <td :colspan="columns.length" class="pa-0" style="overflow: visible">
            <v-card class="w-100 pa-4" variant="flat">
              <v-row class="ml-12">
                <v-col cols="5">
                  <v-row class="pb-6 mt-4 text-h5">{{
                    t("historical_values")
                  }}</v-row>
                  <AnomalyScatterChart
                    :history="item.history"
                    :median="item.median"
                    :lower-bound="item.lowerBound"
                    :upper-bound="item.upperBound"
                    style="width: 100%; height: 300px"
                  />
                </v-col>

                <v-col cols="6" :offset="1">
                  <h5 class="mt-4 text-h5">{{ t("details") }}</h5>
                  <v-skeleton-loader
                    type="paragraph@6"
                    class="ml-n4"
                    v-if="loadingMap[item.id] && !detailsMap[item.id]"
                  ></v-skeleton-loader>
                  <div
                    v-else-if="detailsMap[item.id]?.reasons"
                    v-for="dimObj in dimsForReportType(item.reportType.id)"
                    :key="dimObj.ref"
                  >
                    <div
                      v-for="dimReasons in [
                        getReasonsByDim(
                          detailsMap[item.id].reasons,
                          dimObj.ref,
                        ),
                      ]"
                      :key="dimObj.ref"
                      class="py-0 mt-2"
                    >
                      <h6 class="font-weight-bold text-subtitle-2">
                        {{ dimObj.name }}
                      </h6>
                      <p class="align-center">
                        <span>
                          {{
                            summarizeDimDeviation(
                              dimObj,
                              dimReasons,
                              dimReasons.length,
                              dimReasons[0]?.group_count || 0,
                            )
                          }}
                        </span>
                        <v-tooltip
                          location="top"
                          :text="t('open_in_reporting')"
                        >
                          <template #activator="{ props }">
                            <v-btn
                              v-bind="props"
                              color="secondary"
                              variant="text"
                              :to="flexiRouteDim(item, dimObj.ref)"
                              target="_blank"
                              icon
                              size="x-small"
                            >
                              <v-icon size="small"
                                >fa fa-arrow-up-from-bracket</v-icon
                              >
                            </v-btn>
                          </template>
                        </v-tooltip>
                      </p>

                      <v-row v-if="shouldShowTable(dimReasons)">
                        <v-col cols="8">
                          <v-table
                            class="w-auto border border-gray-300 mb-3"
                            density="compact"
                          >
                            <thead>
                              <tr class="border-b">
                                <th class="border-r px-1">
                                  {{ getDimensionName(dimObj) }}
                                </th>
                                <th class="border-r px-1 text-right">
                                  {{ t("12_month_median") }}
                                </th>
                                <th class="border-r px-1 text-right">
                                  {{ t("labels.value") }}
                                </th>
                                <th class="px-1 text-right">
                                  {{ t("difference_from_median") }}
                                </th>
                              </tr>
                            </thead>
                            <tbody>
                              <tr
                                v-for="reason in dimReasons"
                                :key="reason.target_id_text"
                                class="border-b"
                              >
                                <td class="border-r px-1 py-0.5 text-left">
                                  {{ reason.target_id_text }}
                                </td>
                                <td class="border-r px-1 py-0.5 text-right">
                                  {{ reason.median.toLocaleString() }}
                                </td>
                                <td class="border-r px-1 py-0.5 text-right">
                                  {{ reason.total_value.toLocaleString() }}
                                </td>
                                <td
                                  class="px-1 py-0.5 text-right"
                                  :class="
                                    diffColor(
                                      reason.total_value - reason.median,
                                    )
                                  "
                                >
                                  {{
                                    formatMedianDifference(
                                      reason.total_value - reason.median,
                                    )
                                  }}
                                </td>
                              </tr>
                            </tbody>
                          </v-table>
                        </v-col>
                      </v-row>
                    </div>
                  </div>
                </v-col>
              </v-row>
            </v-card>
          </td>
        </tr>
      </template>
    </v-data-table>
  </v-container>
</template>

<script setup lang="ts">
import DatePicker from "@/components/DatePicker.vue";
import AnomalyScatterChart from "@/components/reporting/AnomalyScatterChart.vue";
import PlatformSelector from "@/components/selectors/PlatformSelector.vue";
import type {
  Anomaly,
  AnomalyReason,
  PlatformBasic,
  ReportTypeBasic,
} from "@/interfaces/reporting";
import { parseDateTime, ymDateFormat } from "@/libs/dates";
import { Dimension } from "@/libs/flexi-reports";
import { toBase64Object } from "@/libs/serialization";
import cancellation from "@/mixins/cancellation";
import reportTypesMixin from "@/mixins/reportTypes";
import axios, { AxiosResponse } from "axios";
import { addDays } from "date-fns/addDays";
import { addMonths } from "date-fns/addMonths";
import { startOfMonth } from "date-fns/startOfMonth";
import { computed, getCurrentInstance, onMounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import type { LocationQueryRaw, RouteLocationRaw } from "vue-router";
import { useRoute } from "vue-router";
import { useStore } from "vuex";

defineOptions({
  name: "AnomalyEmailReportPage",
  mixins: [cancellation, reportTypesMixin],
});

const route = useRoute();
const store = useStore();
const { t, locale } = useI18n();

const organizationId = computed(() => store.state.selectedOrganizationId);

// UI helper
function diffColor(value: number) {
  return value > 0 ? "success" : "error";
}

function shouldShowTable(dimReasons: AnomalyReason[]): boolean {
  return (
    dimReasons.length >= 1 &&
    dimReasons.length < 20 &&
    dimReasons.length !== dimReasons[0].group_count
  );
}

function formatMedianDifference(value: number) {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toLocaleString()}`;
}

// Main Data Table
const headers = computed(() => {
  const base = [
    { key: "data-table-expand" },
    {
      title: t("labels.date"),
      align: "start" as const,
      sortable: true,
      key: "date",
    },
    {
      title: t("organization"),
      align: "start" as const,
      sortable: true,
      key: "organization",
    },
    {
      title: t("platform"),
      align: "start" as const,
      sortable: true,
      key: "platform",
      value: "platform.name",
    },
    {
      title: t("labels.report_type"),
      align: "start" as const,
      sortable: true,
      key: "reportType",
      value: "reportType.name",
    },
    {
      title: t("labels.metric"),
      align: "start" as const,
      sortable: true,
      key: "metric",
    },
    {
      title: t("labels.value"),
      align: "end" as const,
      sortable: true,
      key: "value",
    },
    {
      title: t("12_month_median"),
      align: "end" as const,
      sortable: true,
      key: "median",
    },
    {
      title: t("difference_from_median"),
      align: "end" as const,
      sortable: true,
      key: "differenceFromMedian",
    },
    {
      title: t("significance"),
      align: "end" as const,
      sortable: true,
      key: "significance",
    },
    {
      title: t("open_in_reporting"),
      align: "start" as const,
      sortable: false,
      key: "actions",
    },
  ];

  let filtered = base;

  if (selectedMonthFrom.value === selectedMonthTo.value) {
    filtered = filtered.filter((h) => h.key !== "date");
  }

  if (organizationId.value !== -1) {
    filtered = filtered.filter((h) => h.key !== "organization");
  }

  return filtered;
});

const sortBy = ref([{ key: "significance", order: "desc" as const }]);

const expandedRows = ref([]);

const platformsCount = computed(() => {
  return new Set(anomalyData.value.map((a) => a.platform.short_name)).size;
});

const platformSummary = computed(() => {
  const unique = new Set(anomalyData.value.map((a) => a.platform.short_name));
  return Array.from(unique).join(", ");
});

function significanceLabel(value: number): string {
  if (value <= 10) return t("low");
  if (value <= 25) return t("medium");
  return t("high");
}

// Month + Year Selector Logic

interface MonthYear {
  month: number; // 0-based month
  year: number;
}

// Default date range: last 12 full months ending with the month before last
const defaultMonthTo = ymDateFormat(addMonths(startOfMonth(new Date()), -2));
const defaultMonthFrom = ymDateFormat(addMonths(startOfMonth(new Date()), -13));

const selectedMonthFrom = ref<string>(
  (route.query.month as string) || defaultMonthFrom,
);
const selectedMonthTo = ref<string>(
  (route.query.monthTo as string) || defaultMonthTo,
);

const selectedDatePickerFrom = computed<MonthYear>({
  get() {
    const [year, month] = selectedMonthFrom.value.split("-");
    return { month: parseInt(month, 10) - 1, year: parseInt(year, 10) };
  },
  set(value) {
    selectedMonthFrom.value = `${value.year}-${String(value.month + 1).padStart(
      2,
      "0",
    )}`;
  },
});

const selectedDatePickerTo = computed<MonthYear>({
  get() {
    const [year, month] = selectedMonthTo.value.split("-");
    return { month: parseInt(month, 10) - 1, year: parseInt(year, 10) };
  },
  set(value) {
    selectedMonthTo.value = `${value.year}-${String(value.month + 1).padStart(
      2,
      "0",
    )}`;
  },
});

const lastMonth = ymDateFormat(addDays(startOfMonth(new Date()), -15));
const nowDate = new Date();
// Allow full current year and full previous two years (e.g., in 2025 allow 2025, 2024, 2023)
const minMonthDate = ymDateFormat(new Date(nowDate.getFullYear() - 2, 0, 1));

// show warning that the data may not yet been completely harvested
const showHarvestWarning = computed<boolean>(() => {
  const today: Date = new Date();
  const currentMonth = ymDateFormat(startOfMonth(today));
  const previousMonth = ymDateFormat(addMonths(startOfMonth(today), -1));
  return (
    selectedMonthTo.value === currentMonth ||
    selectedMonthTo.value === previousMonth
  );
});

// Selectors

const selectedPlatform = ref<PlatformBasic | undefined>(undefined);
const selectedReportType = ref<ReportTypeBasic | undefined>(undefined);

// Optional preset from query ?platformId -  only preselects filter, does not affect fetch
const initialPlatformId = ref<number | undefined>(
  route.query.platformId != null
    ? Number(route.query.platformId as string)
    : undefined,
);

const anomalyPlatforms = computed(() => {
  const byId = new Map<string, PlatformBasic>();
  for (const a of anomalyData.value) {
    const p = a.platform;
    if (p && p.id != null && p.name && p.short_name) {
      const key = String(p.id);
      if (!byId.has(key)) {
        byId.set(key, { id: p.id, name: p.name, short_name: p.short_name });
      }
    }
  }
  return Array.from(byId.values()).sort((a, b) => a.name.localeCompare(b.name));
});

const anomalyReportTypes = computed(() => {
  const byId = new Map<number, ReportTypeBasic>();
  for (const a of anomalyData.value) {
    const rt = a.reportType;
    if (rt && rt.id != null) {
      if (!byId.has(rt.id)) byId.set(rt.id, rt);
    }
  }
  return Array.from(byId.values()).sort((a, b) => a.name.localeCompare(b.name));
});

interface AnomalyDetails {
  reasons: AnomalyReason[];
}

const anomalyData = ref<Anomaly[]>([]);
const loadingData = ref(false);
const abortController = ref<AbortController | null>(null);
const detailsMap = ref<Record<number, AnomalyDetails>>({});
const loadingMap = ref<Record<number, boolean>>({});

async function fetchAnomalies() {
  // cancel previous request to avoid hanging
  if (abortController.value) {
    abortController.value.abort();
    abortController.value = null;
  }

  loadingData.value = true;
  abortController.value = new AbortController();
  try {
    let params: {
      month: string | number;
      month_to: string | number;
      organization?: number;
    };

    params = {
      month: selectedMonthFrom.value,
      month_to: selectedMonthTo.value,
    };

    if (organizationId.value != -1) {
      params.organization = organizationId.value;
    }
    const response: AxiosResponse<Anomaly[]> = await axios.get<Anomaly[]>(
      "/api/reporting/anomaly-report/",
      { params, signal: abortController.value.signal },
    );
    anomalyData.value = response.data ?? [];
    // If URL specified platformId, preselect it once after data load
    if (initialPlatformId.value != null) {
      const target = anomalyPlatforms.value.find(
        (p) => p.id === initialPlatformId.value,
      );
      if (target) {
        selectedPlatform.value = target;
      }
      initialPlatformId.value = undefined;
    }
    loadingData.value = false;
  } catch (error) {
    if (axios.isCancel(error)) {
      console.debug("Anomaly fetch cancelled");
      return;
    } else {
      store.dispatch("showSnackbar", {
        content: "Error loading anomaly data: " + error,
        color: "error",
      });
    }
  } finally {
    // ensure source does not hold references if request finished
    abortController.value = null;
  }
  loadingData.value = false;
}

const filteredAnomalies = computed(() => {
  return anomalyData.value.filter((a) => {
    if (selectedPlatform.value && a.platform.id !== selectedPlatform.value.id)
      return false;
    if (
      selectedReportType.value &&
      a.reportType.id !== selectedReportType.value.id
    )
      return false;
    return true;
  });
});

function historyValues(history: Record<string, number>): number[] {
  return Object.values(history);
}

// Dimensions

function getReasonsByDim(
  reasons: AnomalyReason[],
  dim: string,
): AnomalyReason[] {
  return reasons.filter((r) => r.dim === dim);
}

// get all dimensions for a given report type
function dimsForReportType(reportTypeId: number): Dimension[] {
  const vm = getCurrentInstance()?.proxy as any;
  const reportType = vm?.reportTypeMap?.get?.(reportTypeId);
  if (!reportType) return [];
  const baseDims: Dimension[] = Array.from(reportType.dimensionObjs || []);
  // Append a synthetic pseudo-dimension for titles so we also show title reasons
  if (reportType.uses_titles) {
    baseDims.unshift({
      ref: "target",
      name: t("labels.title") || "Title",
      getName: ({ t: tt }: { t: typeof t; locale: typeof locale }) =>
        (tt && tt("labels.title")) || "Title",
    } as unknown as Dimension);
  }
  return baseDims;
}

function getDimensionName(dimObj: Dimension): string {
  const dimName = dimObj.getName({ t, locale });
  return dimName;
}

function summarizeDimDeviation(
  dimObj: Dimension,
  reasons: AnomalyReason[],
  reasonsCount: number,
  dimCount: number,
): string {
  const label = getDimensionName(dimObj);
  if (!dimCount || reasonsCount === 0) {
    return t("none_deviation");
  }
  if (dimCount === 1 && reasonsCount === 1) {
    const reason = reasons[0];
    return t("one_deviation", { label, text: reason.target_id_text });
  }
  if (reasonsCount === dimCount) {
    return t("all_deviation", { reasonsCount, dimCount });
  }
  return t("some_deviation", { reasonsCount, dimCount });
}

// Reporting Connection

function flexiParams(item: Anomaly) {
  return {
    r: ["metric"],
    c: ["date"],
    f: ["organization", "platform", "metric", "date"],
    rt: [item.reportType.id],
    org: [item.organizationId],
    p: [item.platform.id],
    m: [item.metricId],
    run: true,
    st: false,
    dr: {
      start: ymDateFormat(addMonths(parseDateTime(item.date), -12)),
      end: item.date,
    },
    col: true,
  };
}

function flexiRoute(item: Anomaly): RouteLocationRaw {
  return {
    name: "flexitable",
    query: toBase64Object(flexiParams(item)) as unknown as LocationQueryRaw,
  };
}

function flexiRouteDim(item: Anomaly, dim: string): RouteLocationRaw {
  const params = flexiParams(item);
  params.r = [dim];
  return {
    name: "flexitable",
    query: toBase64Object(params) as unknown as LocationQueryRaw,
  };
}

// Watchers

watch([selectedMonthFrom, selectedMonthTo], () => {
  // Preserve existing query params (like platformId) when updating month range
  const newQuery = {
    ...route.query,
    month: selectedMonthFrom.value,
    monthTo: selectedMonthTo.value,
  };
  history.pushState(
    {},
    "",
    route.path + "?" + new URLSearchParams(newQuery as any).toString(),
  );
  fetchAnomalies();
});

watch([organizationId], () => {
  fetchAnomalies();
});

onMounted(async () => {
  // Initialize months from query params
  // if only `month`: set both from/to to `month`
  // if both `month` and `monthTo`: set from/to accordingly
  // if only `monthTo`: set from to earliest available (minMonthDate), to to `monthTo`
  const qMonth = route.query.month as string | undefined;
  const qMonthTo = route.query.monthTo as string | undefined;

  if (qMonth && qMonthTo) {
    selectedMonthFrom.value = qMonth;
    selectedMonthTo.value = qMonthTo;
  } else if (qMonth) {
    selectedMonthFrom.value = qMonth;
    selectedMonthTo.value = qMonth;
  } else if (qMonthTo) {
    selectedMonthFrom.value = minMonthDate;
    selectedMonthTo.value = qMonthTo;
  }

  const vm = getCurrentInstance()?.proxy as any;

  if (vm?.fetchReportTypes) {
    try {
      await vm.fetchReportTypes();
    } catch (e) {
      // ignore
    }
  }
  fetchAnomalies();
});

// Lazy-load anomaly details on expand
watch(
  () => expandedRows.value,
  async (rows: any[]) => {
    for (const id of rows as number[]) {
      // Only fetch if we don't have data and aren't already loading
      if (!detailsMap.value[id] && !loadingMap.value[id]) {
        const anomaly = anomalyData.value.find((a) => a.id === id);
        if (!anomaly) continue;

        loadingMap.value[id] = true;
        try {
          const resp = await axios.get(
            "/api/reporting/anomaly-report/details/",
            {
              params: {
                month: anomaly.date,
                organization: anomaly.organizationId,
                platform: anomaly.platform.id,
                report_type: anomaly.reportType.id,
                metric: anomaly.metricId,
              },
            },
          );
          detailsMap.value[id] = resp.data as AnomalyDetails;
        } catch (e) {
          console.error("Failed to load anomaly details:", e);
        } finally {
          loadingMap.value[id] = false;
        }
      }
    }
  },
  { deep: true },
);
</script>
