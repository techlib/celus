<i18n lang="yaml" src="@/locales/reporting.yaml"></i18n>

<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<template>
  <div class="d-flex align-start">
    <table class="overview text-disabled">
      <tr>
        <th>{{ $t("labels.report_type") }}:</th>
        <td>
          {{ report.reportTypes.map((rt) => rt.name).join(", ") }}
        </td>
      </tr>
      <tr>
        <th>{{ $t("title_fields.split_by") }}:</th>
        <td>
          {{ report.splitBy?.getName($i18n) }}
        </td>
      </tr>
      <tr>
        <th>{{ $t("labels.rows") }}:</th>
        <td>
          {{ report.primaryDimension.getName($i18n) }}
        </td>
      </tr>
      <tr>
        <th>{{ $t("labels.columns") }}:</th>
        <td v-if="report.trendMode">
          {{ $t("trend_mode.trend_mode") }}:
          <em>{{ smartMonthRange(report.baseSubsetDateRange) }}</em>
          vs
          <em>{{ smartMonthRange(report.comparedSubsetDateRange) }}</em>
        </td>
        <td v-else>
          {{ report.groupBy.map((fltr) => fltr.getName($i18n)).join(", ") }}
        </td>
      </tr>
      <tr>
        <th>{{ $t("title_fields.last_modified") }}:</th>
        <td>
          {{ dateAndUser(report.lastUpdated, report.lastUpdatedBy, true) }}
        </td>
      </tr>
      <tr>
        <th>{{ $t("title_fields.created") }}:</th>
        <td>
          {{ dateAndUser(report.created, report.createdBy, true) }}
        </td>
      </tr>
      <tr v-if="!twoPanes">
        <th class="align-top">{{ $t("labels.filters") }}:</th>
        <td>
          <ul class="unobtrusive-bullets">
            <li v-for="fltr in report.filters" :key="fltr.dimension.ref">
              <FilterSpec :fltr="fltr"></FilterSpec>
            </li>
          </ul>
        </td>
      </tr>
      <tr>
        <th class="align-top">{{ $t("labels.settings") }}:</th>
        <td>
          <ul class="unobtrusive-bullets">
            <li>
              {{
                report.includeZeroRows
                  ? $t("show_zero_rows_yes")
                  : $t("show_zero_rows_no")
              }}
            </li>
            <li>
              {{
                report.includeTotals
                  ? $t("show_totals_yes")
                  : $t("show_totals_no")
              }}
            </li>
            <li v-if="report.tagRollUp">{{ $t("tag_roll_up_tt") }}</li>
            <li v-if="report.showUntaggedRemainder">
              <v-tooltip location="bottom">
                <template #activator="{ props }">
                  <span v-bind="props">{{ $t("tags_show_remainder") }}</span>
                </template>
                {{ $t("tags_show_remainder_tt") }}
              </v-tooltip>
            </li>
          </ul>
        </td>
      </tr>
      <slot name="append"></slot>
    </table>
    <!-- second pane with filters -->
    <div v-if="twoPanes" class="overview text-disabled ml-12">
      <div class="font-weight-bold">{{ $t("labels.filters") }}:</div>
      <ul class="unobtrusive-bullets">
        <li v-for="fltr in report.filters" :key="fltr.dimension.ref">
          <FilterSpec :fltr="fltr"></FilterSpec>
        </li>
      </ul>
    </div>
  </div>
</template>

<script>
import { smartMonthRange } from "@/libs/dates";
import FilterSpec from "@/components/reporting/FilterSpec.vue";
import { dateAndUser } from "@/libs/user";

export default {
  name: "ReportSpecOverview",
  components: { FilterSpec },

  props: {
    report: { type: Object },
    twoPanes: { type: Boolean, default: false },
  },

  methods: {
    dateAndUser,
    smartMonthRange,
  },
};
</script>
