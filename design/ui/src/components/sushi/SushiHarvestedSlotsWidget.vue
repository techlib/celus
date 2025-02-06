<i18n lang="yaml" src="@/locales/common.yaml" />
<i18n lang="yaml" src="@/locales/sushi.yaml"></i18n>
<i18n lang="yaml">
en:
  loading_harvest_slots: Checking existing data
  slot_tooltip_: This data will be harvested
  slot_tooltip_sushi: Data was already harvested via SUSHI. Will not harvest.
  slot_tooltip_manual: Data already exists from manual upload. Will not harvest.
  slot_tooltip_broken: The credentials or the report type were marked as broken. Will not harvest.
  slot_tooltip_expired: Data are no longer harvestable.
  slot_tooltip_unknown: Data already exists in the database, probably from a deleted source. Will not harvest.
  slot_tooltip_rh-expired: Data are no longer harvestable via SUSHI. Will not attempt to reharvest.
  slot_tooltip_rh-ok: Data will be reharvested by deleting the existing data and harvesting it again.
  reharvest_warning: Reharvesting will be performed by at first deleting the existing data and then harvesting it again. <strong>If the data is not available anymore, it will be lost</strong>!
  reports_to_harvest: Reports to harvest

cs:
  loading_harvest_slots: Kontroluji existující data
  slot_tooltip_: Tato data budou stažena.
  slot_tooltip_sushi: Data již byla stažena pomocí SUSHI. Stahování nebude provedeno.
  slot_tooltip_manual: Data již existují z manuálního importu. Stahování nebude provedeno.
  slot_tooltip_broken: Přihlašovací údaje nebo report byly označeny jako nefunkční. Stahování nebude provedeno.
  slot_tooltip_expired: Data již nejde stáhnout.
  slot_tooltip_unknown: Data již existují v databázi, pravděpodobně z odstraněného zdroje. Stahování nebude provedeno.
  slot_tooltip_rh-expired: Data již nejde stáhnout pomocí SUSHI. Nebude proveden pokus o znovustažení.
  slot_tooltip_rh-ok: Data budou znovu stažena smazáním existujících dat a jejich opětovným stažením.
  reharvest_warning: Znovu stažení bude provedeno smazáním existujících dat a jejich opětovným stažením. <strong>Pokud data již nejsou dostupná, budou ztracena</strong>!
  reports_to_harvest: Reporty k stažení
</i18n>

<template>
  <div v-if="loading">
    <span class="pr-3">{{ $t("loading_harvest_slots") }}</span>
    <v-progress-linear indeterminate color="primary" />
  </div>
  <div v-else>
    <div class="d-flex">
      <table class="pb-4">
        <tr v-for="type in slots" :key="type">
          <td>
            <v-icon :color="iconColor(type)" small>
              fa-fw {{ icon(type) }}
            </v-icon>
          </td>
          <td class="text-right font-weight-bold caption px-2">
            {{ slotToCount[type] }}
          </td>
          <td class="caption">{{ $t("slot_tooltip_" + type) }}</td>
        </tr>
      </table>
      <v-spacer />
      <div>
        <div class="caption">{{ $t("reports_to_harvest") }}:</div>
        <v-btn-toggle
          v-model="selectedReportTypes"
          multiple
          dense
          class="mb-2"
          color="secondary"
        >
          <v-tooltip
            v-for="rt in availableReportTypes"
            bottom
            max-width="600px"
            :key="rt.id"
          >
            <template #activator="{ on }">
              <v-btn v-on="on" :value="rt.id">
                {{ rt.code }}
              </v-btn>
            </template>
            {{ rt.name }}
          </v-tooltip>
        </v-btn-toggle>
      </div>
    </div>

    <v-alert v-if="reharvestCount" type="warning" outlined class="mb-4">
      <span v-html="$t('reharvest_warning')"></span>
    </v-alert>

    <v-simple-table dense>
      <thead>
        <tr>
          <th>{{ $t("labels.credentials") }}</th>
          <th>{{ $t("labels.report_type") }}</th>
          <th
            v-for="month in monthDates"
            :key="month.toString()"
            class="text-center"
          >
            <span class="font-weight-light">{{ month.getFullYear() }}</span>
            <br />
            <span class="font-weight-black text-center">{{
              month.getMonth() + 1
            }}</span>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, index) in tableData" :key="index">
          <td class="caption">
            <div class="font-weight-bold" v-if="row.cred.title">
              {{ row.cred.title }}
            </div>
            {{ row.cred.organization.name }} / {{ row.cred.platform.name }}
          </td>
          <td class="caption">
            <v-chip
              class="mr-1 px-2"
              :color="row.rt.broken ? '#888888' : 'teal'"
              outlined
              label
            >
              <SushiReportIndicator
                :report="row.rt"
                show-last-harvestable-month
              />
            </v-chip>
          </td>
          <td
            v-for="(month, index2) in months"
            :key="`${index}-${index2}`"
            class="text-center"
          >
            <!-- reharvest with data present -->
            <v-tooltip
              v-if="reharvest && dataPresent(row.months[month])"
              bottom
              max-width="600px"
              :key="`tt-${index}-${index2}`"
            >
              <template #activator="{ on }">
                <span v-on="on">
                  <v-icon
                    v-if="dataHarvestable(row.cred, row.rt, month)"
                    color="warning lighten-1"
                    small
                    class="ml-1"
                    >fa fa-sync-alt</v-icon
                  >
                  <v-icon v-else color="error lighten-1" small class="ml-1"
                    >fa fa-exclamation-triangle</v-icon
                  >
                </span>
              </template>
              {{
                dataHarvestable(row.cred, row.rt, month)
                  ? $t("reharvest_will_do_tt")
                  : $t("reharvest_data_not_available_tt")
              }}
            </v-tooltip>
            <!-- new harvest or no data present -->
            <v-tooltip bottom v-else>
              <template #activator="{ on }">
                <v-icon v-on="on" :color="iconColor(row.months[month])" small
                  >fa {{ icon(row.months[month]) }}
                </v-icon>
              </template>
              {{ $t(`slot_tooltip_${row.months[month]}`) }}
              <br />
              <span
                v-if="
                  row.months[month] === 'expired' &&
                  row.rt.last_harvestable_month_user_id
                "
              >
                {{ $t("sushi.state_desc.last_harvestable_month_set_by_user") }}
              </span>
              <span
                v-else-if="
                  row.months[month] === 'expired' &&
                  row.rt.last_harvestable_month_attempt_id
                "
              >
                {{
                  $t("sushi.state_desc.last_harvestable_month_set_by_harvest")
                }}
              </span>
            </v-tooltip>
          </td>
        </tr>
      </tbody>
    </v-simple-table>
  </div>
</template>

<script>
import cancellation from "@/mixins/cancellation";
import { mapActions } from "vuex";
import { monthsBetween, parseDateTime, ymDateFormat } from "@/libs/dates";
import SushiReportIndicator from "@/components/sushi/SushiReportIndicator";

export default {
  name: "SushiHarvestedSlotsWidget",

  components: {
    SushiReportIndicator,
  },
  mixins: [cancellation],

  props: {
    credentials: { type: Array, required: true },
    startDate: { type: String, required: true },
    endDate: { type: String, required: true },
    ready: { type: Boolean },
    reharvest: { type: Boolean, default: false },
  },

  data() {
    let rts = new Set();
    this.credentials.forEach((cr) =>
      cr.counter_reports_long.forEach((rt) => rts.add(rt.id))
    );
    return {
      presenceData: [],
      presenceMap: new Map(),
      loading: false,
      dataReady: this.ready,
      selectedReportTypes: Array.from(rts),
    };
  },

  computed: {
    presenceDataUrl() {
      if (this.startDate && this.endDate && this.credentials.length) {
        let credIds = this.credentials.map((cr) => cr.pk).join(",");
        return `/api/import-batch/data-presence/?start_date=${this.startDate}&end_date=${this.endDate}&credentials=${credIds}`;
      }
      return null;
    },
    months() {
      return this.monthDates.map(ymDateFormat);
    },
    monthDates() {
      return monthsBetween(this.startDate, this.endDate);
    },
    tableData() {
      let rows = [];
      if (this.startDate && this.endDate && this.credentials.length) {
        for (let cred of this.credentials) {
          for (let rt of cred.counter_reports_long) {
            // only selected report types
            if (!this.selectedReportTypes.includes(rt.id)) continue;
            let monthData = {};
            const last_harvestable_month = rt.last_harvestable_month
              ? rt.last_harvestable_month.slice(0, 7)
              : null;
            for (let month of this.months) {
              if (rt.broken || cred.broken) {
                monthData[month] = "broken";
                continue;
              }
              let key = `${rt.report_type}#${cred.platform.pk}#${cred.organization.pk}#${month}`;
              monthData[month] = this.presenceMap.get(key) ?? "";
              // if no data is present, we can reharvest or not, but we do
              // not need to take reharvest into account
              if (monthData[month] === "") {
                monthData[month] =
                  last_harvestable_month && last_harvestable_month > month
                    ? "expired"
                    : "";
                continue;
              }
              // sushi not broken and there is some data present
              // we either leave the data as it is, or in reharvest mode
              // we want to check the last harvestable month
              if (this.reharvest) {
                monthData[month] =
                  last_harvestable_month && last_harvestable_month > month
                    ? "rh-expired"
                    : "rh-ok";
              }
            }
            rows.push({ cred: cred, rt: rt, months: monthData });
          }
        }
      }
      rows.sort(
        (a, b) =>
          a.cred.organization.name.localeCompare(b.cred.organization.name) ||
          a.cred.platform.name.localeCompare(b.cred.platform.name)
      );
      return rows;
    },
    slotsFree() {
      return (this.slotToCount[""] ?? 0) + (this.slotToCount["rh-ok"] ?? 0);
    },
    slotToCount() {
      let out = {};
      this.tableData.forEach((row) =>
        Object.values(row.months).forEach((value) => {
          out[value] ??= 0;
          out[value]++;
        })
      );
      return out;
    },
    slots() {
      return Object.keys(this.slotToCount).sort();
    },
    reharvestCount() {
      return this.slotToCount["rh-ok"] ?? 0;
    },
    availableReportTypes() {
      let out = new Map();
      this.credentials.forEach((cr) =>
        cr.counter_reports_long.forEach((rt) => out.set(rt.id, rt))
      );
      let array = Array.from(out.values());
      array.sort((a, b) => a.code.localeCompare(b.code));
      return array;
    },
  },

  methods: {
    ...mapActions({ showSnackbar: "showSnackbar" }),
    async fetchPresenceData() {
      if (!this.presenceDataUrl) return;
      this.loading = true;
      this.dataReady = false;
      let result = await this.http({
        url: this.presenceDataUrl,
        group: "data-presence",
      });
      this.loading = false;
      if (!result.error) {
        this.presenceData = result.response.data;
        let map = new Map();
        this.presenceData.forEach((rec) =>
          map.set(
            `${rec.report_type_id}#${rec.platform_id}#${
              rec.organization_id
            }#${ymDateFormat(parseDateTime(rec.date))}`,
            rec.source
          )
        );
        this.presenceMap = map;
        this.dataReady = true;
      }
    },
    icon(status) {
      switch (status) {
        case "sushi":
          return "fa-file-download";
        case "manual":
          return "fa-file-import";
        case "broken":
          return "fa-times-circle";
        case "expired":
          return "fa-calendar-alt";
        case "unknown":
          return "fa-database";
        case "rh-expired":
          return "fa-calendar-alt";
        case "rh-ok":
          return "fa-sync-alt";
        default:
          return "fa-cloud-download-alt";
      }
    },
    iconColor(status) {
      switch (status) {
        case "sushi":
        case "manual":
          return "#dddddd";
        case "broken":
          return "#ffaaaa";
        case "expired":
          return "warning lighten-2";
        case "unknown":
        case "rh-expired":
          return "error lighten-1";
        case "rh-ok":
          return "warning lighten-1";
        default:
          return "success";
      }
    },
    dataPresent(status) {
      return status === "sushi" || status === "manual" || status === "unknown";
    },
    dataHarvestable(credentials, report, month) {
      return (
        !report.broken &&
        !credentials.broken &&
        (!report.last_harvestable_month ||
          report.last_harvestable_month <= month)
      );
    },
  },

  watch: {
    presenceDataUrl: {
      immediate: true,
      handler() {
        this.fetchPresenceData();
      },
    },
    dataReady() {
      this.$emit("update:ready", this.dataReady);
    },
  },
};
</script>

<style scoped></style>
