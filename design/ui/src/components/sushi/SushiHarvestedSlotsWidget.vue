<i18n lang="yaml" src="@/locales/common.yaml" />
<i18n lang="yaml">
en:
  loading_harvest_slots: Checking existing data
  slot_tooltip_: This data will be harvested
  slot_tooltip_sushi: Data was already harvested via SUSHI. Will not harvest.
  slot_tooltip_manual: Data already exists from manual upload. Will not harvest.
  slot_tooltip_broken: The credentials or the report type were marked as broken. Will not harvest.
  slot_tooltip_unknown: Data already exists in the database, probably from a deleted source. Will not harvest.

cs:
  loading_harvest_slots: Kontroluji existující data
  slot_tooltip_: Tato data budou stažena.
  slot_tooltip_sushi: Data již byla stažena pomocí SUSHI. Stahování nebude provedeno.
  slot_tooltip_manual: Data již existují z manuálního importu. Stahování nebude provedeno.
  slot_tooltip_broken: Přihlašovací údaje nebo report byly označeny jako nefunkční. Stahování nebude provedeno.
  slot_tooltip_unknown: Data již existují v databázi, pravděpodobně z odstraněného zdroje. Stahování nebude provedeno.
</i18n>

<template>
  <div v-if="loading">
    <span class="pr-3">{{ $t("loading_harvest_slots") }}</span>
    <v-progress-linear indeterminate color="primary" />
  </div>
  <div v-else>
    <table class="pb-4">
      <tr v-for="type in presentSlotTypes" :key="type">
        <td>
          <v-icon v-if="type === ''" color="success" small>
            fa fa-fw fa-cloud-download-alt</v-icon
          >
          <v-icon v-else-if="type === 'sushi'" color="#dddddd" small
            >fa fa-fw fa-file-download
          </v-icon>
          <v-icon v-else-if="type === 'manual'" color="#dddddd" small
            >fa fa-fw fa-file-import
          </v-icon>
          <v-icon v-else-if="type === 'broken'" color="#ffaaaa" small
            >far fa-fw fa-times-circle
          </v-icon>
          <v-icon v-else color="#00ff00" small>fa fa-fw fa-database</v-icon>
        </td>
        <td>
          <span class="text-right font-weight-bold caption px-2">{{
            slotCount(type)
          }}</span>
        </td>
        <td>
          <span class="caption">{{ $t("slot_tooltip_" + type) }}</span>
        </td>
      </tr>
    </table>
    <v-simple-table dense>
      <thead>
        <tr>
          <th>{{ $t("labels.credentials") }}</th>
          <th>{{ $t("labels.report_type") }}</th>
          <th v-for="month in months" :key="month">
            {{ month }}
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
          <td class="caption">{{ row.rt.code }}</td>
          <td v-for="(month, index2) in months" :key="`${index}-${index2}`">
            <v-tooltip bottom>
              <template #activator="{ on }">
                <span v-on="on">
                  <v-icon
                    v-if="row.months[month] === 'sushi'"
                    color="#dddddd"
                    small
                    >fa fa-file-download
                  </v-icon>
                  <v-icon
                    v-else-if="row.months[month] === 'manual'"
                    color="#dddddd"
                    small
                    >fa fa-file-import
                  </v-icon>
                  <v-icon
                    v-else-if="row.months[month] === 'broken'"
                    color="#ffaaaa"
                    small
                    >far fa-times-circle
                  </v-icon>
                  <v-icon
                    v-else-if="row.months[month] === 'unknown'"
                    color="#ff0000"
                    small
                    >fa fa-database
                  </v-icon>
                  <v-icon v-else color="success" small
                    >fa fa-cloud-download-alt</v-icon
                  >
                </span>
              </template>
              {{ $t(`slot_tooltip_${row.months[month]}`) }}
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

export default {
  name: "SushiHarvestedSlotsWidget",
  mixins: [cancellation],

  props: {
    credentials: { type: Array, required: true },
    startDate: { type: String, required: true },
    endDate: { type: String, required: true },
    ready: { type: Boolean },
  },

  data() {
    return {
      presenceData: [],
      presenceMap: new Map(),
      loading: false,
      dataReady: this.ready,
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
      return monthsBetween(this.startDate, this.endDate).map(ymDateFormat);
    },
    tableData() {
      let rows = [];
      if (this.startDate && this.endDate && this.credentials.length) {
        for (let cred of this.credentials) {
          for (let rt of cred.counter_reports_long) {
            let monthData = {};
            for (let month of this.months) {
              if (rt.broken || cred.broken) {
                monthData[month] = "broken";
              } else {
                let key = `${rt.report_type}#${cred.platform.pk}#${cred.organization.pk}#${month}`;
                monthData[month] = this.presenceMap.get(key) ?? "";
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
    slotsTotal() {
      let result = 0;
      this.tableData.forEach(
        (row) => (result += Object.values(row.months).length)
      );
      return result;
    },
    slotCount() {
      return function (type) {
        let result = 0;
        this.tableData.forEach(
          (row) =>
            (result += Object.values(row.months).filter(
              (value) => value === type
            ).length)
        );
        return result;
      };
    },
    slotsFree() {
      return this.slotCount("");
    },
    presentSlotTypes() {
      let types = new Set();
      this.tableData.forEach((row) =>
        Object.values(row.months).forEach((value) => types.add(value))
      );
      return [...types];
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
