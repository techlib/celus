<i18n lang="yaml">
en:
  output_logs: Generated logs
  imported_months: Data found for months
  overview: Overview
  upload: Upload
  total_hits: Sum of hits
  imported_metrics: Found metrics
  found_dimensions: Found dimensions
  imported_organizations: Found organizations
  title_count: Title count
  hits: hits
  is_interest_metric: This metric defines interest for this report type
  data_exists: Data for this month already exists.
  metric_create: Metric will be created.
  metric_ready: Metric is valid and is used.
  metric_unknown: Metric was not found.
  metric_check_failed: Invalid metric for report type.
  metric_not_used_yet: |
    Metric hasn't been used for this combination of organization,
    platform and report type.
  import_not_allowed: Data import is not possible
  data_exists_for_months: Data are already present for following months
  delete_existing_data_first: If you want to proceed you need to delete existing data first.
  cant_use_metrics: Following metrics can't be used
  month_table:
    hits_sum: Sum of hits
    prev_year_average: Previous year average
    prev_year_month: Same month previous year
    sum_count_tooltip: Sum of hits which are present in uploaded data per month
    last_year_average_tooltip: Average sum of hits for previous year
    last_year_month_tooltip: Sum of hits for the same month last year
  comparison_with_existing_sum: Comparison with the sum of hits with existing data
  comparison_with_last_year_average_sum: Comparison with the average sum of hits from previous year
  comparison_with_last_year_month_sum: Comparison with sum of hits from the same month previous year
  organization_not_found: Could not match this organization with an existing one.
  organization_raw_data_disabled: Raw non-counter data import is disabled for this organization.
  organizations_were_not_found: The following organizations defined in the file were not found, thus data can't be imported
  organizations_not_found_fix: Please make sure that the provided name(s) matches the names from
  organizations_not_found_fix_list: the organization list
  organizations_with_raw_import_disabled: Raw data import is disabled for the following organizations, thus data can't be imported

cs:
  output_logs: Vygenerované záznamy
  imported_months: Data nalezena pro měsíce
  overview: Přehled
  upload: Nahrát
  total_hits: Součet zásahů
  imported_metrics: Nalezené metriky
  found_dimensions: Nalezené dimenze
  imported_organizations: Nalezené organizace
  title_count: Počet titulů
  hits: zásahů
  is_interest_metric: Tato metrika definuje zájem pro tento typ reportu
  data_exists: Data za tento měsíc již existují.
  metric_create: Metrika bude vytvořena.
  metric_ready: Metrika je platná a používaná.
  metric_unknown: Metrika nebyla nalezena.
  metric_check_failed: Metrika není pro daný report povolená.
  metric_not_used_yet: |
    Tato metrika zatím nebyla použita pro danu kombinaci
    organizace platformy a typu reportu.
  import_not_allowed: Import dat není možný
  data_exists_for_months: Data za následující měsíce již existují
  delete_existing_data_first: Pokud chcete pokračovat je nutné nejprve smazat existující data.
  cant_use_metrics: Následující metriky nemohou být použity
  month_table:
    hits_sum: Součet zásahů
    prev_year_average: Průměr za předchozí rok
    prev_year_month: Stejný měsíc předchozí rok
    sum_count_tooltip: Součet zásahů, které jsou přítomné v nahrávaných datech po měsících
    last_year_average_tooltip: Průměrný součet zásahů za předchozí rok
    last_year_month_tooltip: Součet zásahů za stejný měsíc předchozího roku
  comparison_with_existing_sum: Porovnání součtu zásahů s již existujícími daty
  comparison_with_last_year_average_sum: Porovnání součtu zásahů s průměrem součtu zásahů za minulý rok
  comparison_with_last_year_month_sum: Porovnání součtu zásahů se stejným měsícem v minulém roce
  organization_not_found: Nebylo možné namapovat tuto organizaci na existující organizace.
  organization_raw_data_disabled: Pro tuto organizaci není dovoleno nahrávat surová data v ne-COUNTER formátu.
  organizations_were_not_found: Vyznačené organizace, které jsou definované v souboru, nebyly nalezeny a kvůli tomu nemohou být data naimportována
  organizations_not_found_fix: Prosím ujistěte se, poskytnutá jména odpovídají jménům u
  organizations_not_found_fix_list: seznamu organizací
  organizations_with_raw_import_disabled: Pro následující organizace není dovoleno nahrávat surová data a není tedy možné data naimportovat
</i18n>

<template>
  <v-container fluid>
    <v-row>
      <v-col cols="auto" v-if="!wrongOrganizationPresent">
        <v-card hover>
          <v-card-text>
            <h4>{{ $t("output_logs") }}</h4>
            <div class="text-right">
              {{ formatInteger(preflightData.log_count) }}
            </div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="auto" v-if="!wrongOrganizationPresent">
        <v-card hover>
          <v-card-text>
            <h4>{{ $t("total_hits") }}</h4>
            <div class="text-right">
              {{ formatInteger(preflightData.hits_total) }}
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="auto" v-if="!wrongOrganizationPresent">
        <v-card hover>
          <v-card-text>
            <h4>{{ $t("title_count") }}</h4>
            <div class="text-right">{{ formatInteger(titleCount) }}</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="auto" v-if="!wrongOrganizationPresent">
        <v-card hover>
          <v-card-text>
            <h4>{{ $t("imported_months") }}</h4>
            <br />
            <div class="text-right">
              <table style="width: 100%">
                <tr class="text-center">
                  <th class="pl-1 pr-1"></th>
                  <th class="pl-1 pr-1">
                    <v-tooltip bottom>
                      <template v-slot:activator="{ on }">
                        <span v-on="on">{{ $t("month_table.hits_sum") }}</span>
                      </template>
                      <span>{{ $t("month_table.sum_count_tooltip") }}</span>
                    </v-tooltip>
                  </th>
                  <th class="pl-1 pr-1" v-if="clashingMonths.length == 0">
                    <v-tooltip bottom>
                      <template v-slot:activator="{ on }">
                        <span v-on="on">
                          {{ $t("month_table.prev_year_average") }}
                        </span>
                      </template>
                      <span>
                        {{ $t("month_table.last_year_average_tooltip") }}
                      </span>
                    </v-tooltip>
                  </th>
                  <th class="pl-1 pr-1" v-if="clashingMonths.length == 0">
                    <v-tooltip bottom>
                      <template v-slot:activator="{ on }">
                        <span v-on="on">
                          {{ $t("month_table.prev_year_month") }}
                        </span>
                      </template>
                      <span>
                        {{ $t("month_table.last_year_month_tooltip") }}
                      </span>
                    </v-tooltip>
                  </th>
                </tr>
                <tr v-for="rec in monthsSorted" :key="rec.name">
                  <td class="text-left pr-4">
                    {{ rec.name.substring(0, 7) }}

                    <v-tooltip
                      bottom
                      v-if="preflightData.clashing_months.includes(rec.name)"
                    >
                      <template v-slot:activator="{ on }">
                        <v-icon class="ml-1" x-small color="error" v-on="on">
                          fa fa-exclamation-triangle
                        </v-icon>
                      </template>
                      <span>{{ $t("data_exists") }}</span>
                    </v-tooltip>
                  </td>
                  <td class="text-center">
                    <SimpleCompare
                      :value="rec.value.new && rec.value.new.sum"
                      :other-value="
                        rec.value.this_month && rec.value.this_month.sum
                      "
                      :other-value-tooltip="$t('comparison_with_existing_sum')"
                      :negate="false"
                    />
                  </td>
                  <td v-if="clashingMonths.length == 0" class="text-center">
                    <SimpleCompare
                      :value="
                        rec.value.prev_year_avg && rec.value.prev_year_avg.sum
                      "
                      :other-value="rec.value.new && rec.value.new.sum"
                      :other-value-tooltip="
                        $t('comparison_with_last_year_average_sum')
                      "
                      :negate="true"
                    />
                  </td>
                  <td v-if="clashingMonths.length == 0" class="text-center">
                    <SimpleCompare
                      :value="
                        rec.value.prev_year_month &&
                        rec.value.prev_year_month.sum
                      "
                      :other-value="rec.value.new && rec.value.new.sum"
                      :other-value-tooltip="
                        $t('comparison_with_last_year_month_sum')
                      "
                      :negate="true"
                    />
                  </td>
                </tr>
              </table>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="auto" v-if="!wrongOrganizationPresent">
        <v-card hover>
          <v-card-text>
            <h4>{{ $t("imported_metrics") }}</h4>
            <div class="text-right">
              <table>
                <tr v-for="rec in metricsSorted" :key="rec.name">
                  <v-tooltip bottom>
                    <template #activator="{ on }">
                      <td class="text-left">
                        <v-icon
                          v-on="on"
                          small
                          left
                          :color="metricState(rec.name).color"
                        >
                          {{ metricState(rec.name).icon }}
                        </v-icon>
                      </td>
                    </template>
                    {{ $t(metricState(rec.name).tooltip) }}
                  </v-tooltip>
                  <td class="text-left pr-4">
                    <v-tooltip v-if="isInterestMetric(rec.name)" bottom>
                      <template #activator="{ on }">
                        <span v-on="on">
                          {{ rec.name }}
                          <v-icon class="ml-2" x-small>fa fa-star</v-icon>
                        </span>
                      </template>
                      {{ $t("is_interest_metric") }}
                    </v-tooltip>
                    <span v-else v-text="rec.name"></span>
                  </td>
                  <td>{{ formatInteger(rec.value.sum) }}</td>
                </tr>
              </table>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col
        cols="auto"
        v-if="!wrongOrganizationPresent && foundDimensions.length > 0"
      >
        <v-card hover>
          <v-card-text>
            <h4>{{ $t("found_dimensions") }}</h4>
            <div class="text-right">
              <table>
                <tr v-for="rec in foundDimensions" :key="rec">
                  <td>{{ rec }}</td>
                </tr>
              </table>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="auto">
        <v-card hover v-if="organizationsSorted">
          <v-card-text>
            <h4>{{ $t("imported_organizations") }}</h4>
            <div class="text-right">
              <table>
                <tr v-for="rec in organizationsSorted" :key="rec.name">
                  <td class="text-left pr-4">
                    <v-tooltip v-if="!rec.value.pk" bottom>
                      <template #activator="{ on }">
                        <span v-on="on">
                          {{ rec.name }}
                          <v-icon class="ml-1" x-small color="error" v-on="on">
                            fa fa-exclamation-triangle
                          </v-icon>
                        </span>
                      </template>
                      {{ $t("organization_not_found") }}
                    </v-tooltip>
                    <v-tooltip
                      v-else-if="
                        method == 'raw' &&
                        rawDisabledPk.includes(rec.value.pk)
                      "
                      bottom
                    >
                      <template #activator="{ on }">
                        <span v-on="on">
                          {{ rec.name }}
                          <v-icon class="ml-1" x-small color="error" v-on="on">
                            fa fa-exclamation-triangle
                          </v-icon>
                        </span>
                      </template>
                      {{ $t("organization_raw_data_disabled") }}
                    </v-tooltip>
                    <span v-else v-text="rec.name"></span>
                  </td>
                  <td>{{ formatInteger(rec.value.sum) }}</td>
                </tr>
              </table>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
    <v-row v-if="wrongOrganizationPresent">
      <v-col>
        <v-alert type="error" outlined>
          <h4 class="mb-2 text-h6">{{ $t("import_not_allowed") }}</h4>
          <div class="mb-2" v-if="notFoundOrg.length > 0">
            {{ $t("organizations_were_not_found") }}:
            <ul class="pt-1">
              <li v-for="org in notFoundOrg" :key="org.name">
                {{ org.name }}
              </li>
            </ul>
            <p class="mt-2">
              <strong>
                {{ $t("organizations_not_found_fix") }}
                <router-link :to="{ name: 'organization-list' }">
                  {{ $t("organizations_not_found_fix_list") }}
                </router-link>
                .
              </strong>
            </p>
          </div>
          <div class="mb-2" v-if="rawDisabledOrg.length > 0">
            {{ $t("organizations_with_raw_import_disabled") }}:
            <ul class="pt-1">
              <li v-for="org in rawDisabledOrg" :key="org.name">
                {{ org.name }}
              </li>
            </ul>
          </div>
        </v-alert>
      </v-col>
    </v-row>
    <v-row v-else-if="clashingMonths.length > 0 || failedMetrics.length > 0">
      <v-col>
        <v-alert type="error" outlined>
          <h4 class="mb-2 text-h6">{{ $t("import_not_allowed") }}</h4>
          <div v-if="clashingMonths.length > 0" class="mb-2">
            {{ $t("data_exists_for_months") }}:
            <ul class="pt-1">
              <li v-for="month in clashingMonths" :key="month">
                {{ month.substring(0, 7) }}
              </li>
            </ul>
            <p v-if="failedMetrics.length === 0" class="mt-2">
              <strong>{{ $t("delete_existing_data_first") }}</strong>
            </p>
          </div>
          <div v-if="failedMetrics.length > 0" class="mb-2">
            {{ $t("cant_use_metrics") }}:
            <ul class="pt-1">
              <li v-for="metric in failedMetrics" :key="metric.name">
                <span class="font-weight-medium">{{ metric.name }}</span>
                -
                <span class="font-weight-light">{{
                  $t(metricState(metric.name).tooltip)
                }}</span>
              </li>
            </ul>
          </div>
        </v-alert>
      </v-col>
    </v-row>
  </v-container>
</template>
<script>
import SimpleCompare from "@/components/util/SimpleCompare";
import { formatInteger } from "@/libs/numbers";

export default {
  name: "ImportPreflightDataWidget",

  components: {
    SimpleCompare,
  },

  props: {
    preflightData: { required: true, type: Object },
    interestMetrics: { required: false, type: Array, default: () => [] },
    metrics: { required: true, type: Array, default: () => [] },
    usableMetrics: { required: true, type: Array },
    checkMetrics: {
      required: false,
      type: Boolean,
      default: () => false,
    },
    autoCreateMetrics: { required: true, type: Boolean },
    method: { required: true, type: String },
    rawDisabledPerOrganization: { required: false, default: [] },
  },

  computed: {
    monthsSorted() {
      return Object.entries(this.preflightData.months)
        .map(([key, value]) => {
          return { name: key, value: value };
        })
        .sort((a, b) => a.name.localeCompare(b.name));
    },
    metricsSorted() {
      return Object.entries(this.preflightData.metrics)
        .map(([key, value]) => {
          return { name: key, value: value };
        })
        .sort((a, b) => b.value.sum - a.value.sum);
    },
    organizationsSorted() {
      if (!this.preflightData.organizations) {
        return null;
      }
      return Object.entries(this.preflightData.organizations)
        .map(([key, value]) => {
          return { name: key, value: value };
        })
        .sort((a, b) => a.name.localeCompare(b.name));
    },
    titleCount() {
      return this.preflightData.title_count;
    },
    existingMetricsNames() {
      return this.metrics.map((e) => e.short_name);
    },
    failedMetrics() {
      if (!this.checkMetrics) {
        return [];
      }
      return this.metricsSorted.filter(
        (e) => !this.usableMetrics.includes(e.name)
      );
    },
    clashingMonths() {
      return this.preflightData.clashing_months;
    },
    rawDisabledOrg() {
      if (this.organizationsSorted && this.method == "raw") {
        return this.organizationsSorted.filter(
          (e) => !!e.value.pk && this.rawDisabledPk.includes(e.value.pk)
        );
      } else {
        return [];
      }
    },
    notFoundOrg() {
      if (this.organizationsSorted) {
        return this.organizationsSorted.filter((e) => !e.value.pk);
      } else {
        return [];
      }
    },
    wrongOrganizationPresent() {
      return this.notFoundOrg.length > 0 || this.rawDisabledOrg.length > 0;
    },
    usedMetrics() {
      return this.preflightData.used_metrics;
    },
    foundDimensions() {
      return this.preflightData.dimensions || [];
    },
    rawDisabledPk() {
      return this.rawDisabledPerOrganization.map((e) => e.pk);
    },
  },

  methods: {
    formatInteger,
    isInterestMetric(metricName) {
      if (this.interestMetrics.indexOf(metricName) > -1) {
        return true;
      }
      return false;
    },
    metricState(metricName) {
      if (this.checkMetrics) {
        if (!this.usableMetrics.includes(metricName)) {
          // Metric check failed
          return {
            icon: "fas fa-exclamation-circle",
            color: "error",
            tooltip: "metric_check_failed",
          };
        }
      }
      if (this.autoCreateMetrics) {
        if (!this.existingMetricsNames.includes(metricName)) {
          return {
            icon: "fas fa-plus-circle",
            color: "info",
            tooltip: "metric_create",
          };
        }
      } else {
        if (!this.existingMetricsNames.includes(metricName)) {
          return {
            icon: "fas fa-exclamation-circle",
            color: "error",
            tooltip: "metric_unknown",
          };
        }
      }
      if (!this.usedMetrics.includes(metricName)) {
        // Metric exists and is valid, but it hasn't been used
        // for this combination of (org, platform, report type)
        return {
          icon: "fas fa-question-circle",
          color: "warning",
          tooltip: "metric_not_used_yet",
        };
      }
      return {
        icon: "fas fa-check-circle",
        color: "success",
        tooltip: "metric_ready",
      };
    },
  },
};
</script>
<style scoped lang="scss">
ul.no-decoration {
  list-style: none;
}
</style>
