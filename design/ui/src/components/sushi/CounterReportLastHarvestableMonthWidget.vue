<template>
  <!-- the v-if below makes sure the component is not rendered before the data is loaded -->
  <LastHarvestableMonthEntryWidget
    v-if="counterReports.length > 0"
    v-model="reportIdToDate"
    :counter-reports-ordered="counterReportsOrdered"
    :loading="saving"
    multiple-credentials
    @close="closeDialog(false)"
    @apply="trigger"
  ></LastHarvestableMonthEntryWidget>
</template>

<script>
import { mapActions } from "vuex";
import cancellation from "@/mixins/cancellation";
import LastHarvestableMonthEntryWidget from "@/components/sushi/LastHarvestableMonthEntryWidget.vue";

export default {
  name: "CounterReportLastHarvestableMonthWidget",

  components: {
    LastHarvestableMonthEntryWidget,
  },

  mixins: [cancellation],

  props: {
    credentials: {
      required: true,
      type: Array,
    },
  },

  data() {
    return {
      counterReports: [],
      saving: false,
      reportIdToDate: null,
    };
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    preprocessPerCounterReport() {
      let counterReports = {};
      this.credentials.forEach((cred) => {
        for (const cr of cred.counter_reports_long) {
          if (counterReports[cr.id]) {
            if (
              (cr.last_harvestable_month || "9999-99-99") <
              (counterReports[cr.id] || "9999-99-99")
            ) {
              counterReports[cr.id].last_harvestable_month =
                cr.last_harvestable_month;
            }
          } else {
            counterReports[cr.id] = { ...cr };
          }
          if (counterReports[cr.id].last_harvestable_month) {
            // 2020-01-01 -> 2020-01
            counterReports[cr.id].last_harvestable_month = counterReports[
              cr.id
            ].last_harvestable_month.slice(0, 7);
          }
        }
      });
      this.counterReports = Object.values(counterReports);
    },
    closeDialog(refresh) {
      this.$emit("close", refresh);
    },
    async trigger() {
      this.saving = true;
      const result = await this.http({
        method: "post",
        url: this.triggerUrl,
        data: this.dataForTrigger,
      });
      if (!result.error) {
        this.closeDialog(result.response.data.updated > 0);
      }
      this.saving = false;
    },
  },

  computed: {
    triggerUrl() {
      return "/api/sushi-credentials/update-assigned-counter-reports/";
    },
    counterReportsOrdered() {
      return Object.values(this.counterReports).sort(
        (a, b) =>
          a.counter_version - b.counter_version || a.name.localeCompare(b.name),
      );
    },
    dataForTrigger() {
      return this.credentials
        .map((cred) =>
          cred.counter_reports_long.map((cr) => {
            const lhm = this.reportIdToDate
              ? this.reportIdToDate[cr.id] || null
              : null;
            return {
              credentials_id: cred.pk,
              counter_report_id: cr.id,
              last_harvestable_month: lhm === null ? null : `${lhm}-01`,
            };
          }),
        )
        .flat();
    },
  },

  mounted() {
    this.preprocessPerCounterReport();
  },
};
</script>

<style lang="scss"></style>
