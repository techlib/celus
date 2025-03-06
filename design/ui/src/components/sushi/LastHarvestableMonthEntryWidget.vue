<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<i18n lang="yaml" src="@/locales/dialog.yaml"></i18n>

<i18n lang="yaml">
en:
  title: Set last harvestable month
  desc: |
    If you know that data is not available before a certain date for a
    specific report, you can set this date here. CELUS will use this information
    and not try to harvest data before this date.
  desc2_1: The date is set per report and applied to all credentials you have currently selected.
  desc2_2: To unset a previously set date, just remove the date and hit apply.
  apply: Apply
  copy_tt: Copy date from previous entry
cs:
  title: Nastavete od kdy jsou data k dispozici
  desc: |
    Pokud víte, že data nejsou dostupná před určitým datem pro konkrétní
    report, můžete toto datum nastavit zde. CELUS bude tuto informaci používat a
    nebude se snažit data stáhnout před tímto datem.
  desc2_1: Datum je nastaveno pro každý report a aplikováno na všechny přihlašovací údaje, které máte aktuálně vybrané.
  desc2_2: Chcete-li zrušit dříve nastavené datum, stačí odstranit hodnotu data a stisknout tlačítko Nastavit.
  apply: Nastavit
  copy_tt: Zkopírovat datum z předchozího záznamu
</i18n>

<template>
  <v-card>
    <v-card-title>{{ $t("title") }}</v-card-title>
    <v-card-text>
      <v-row>
        <v-col>
          <p>{{ $t("desc") }}</p>
          <p>
            <span v-if="multipleCredentials">{{ $t("desc2_1") }} </span>
            <span>{{ $t("desc2_2") }}</span>
          </p>
        </v-col>
      </v-row>
      <v-row class="mt-0">
        <v-col>
          <table class="mx-auto">
            <tr v-for="(cr, index) in counterReportsOrdered" :key="cr.id">
              <th class="text-left pr-3 pt-4">
                <v-chip
                  class="mr-1 px-2"
                  :color="cr.broken ? '#888888' : 'teal'"
                  variant="outlined"
                  label
                >
                  <SushiReportIndicator :report="cr"></SushiReportIndicator>
                </v-chip>
              </th>
              <td style="min-width: 140px">
                <MonthEntry v-model="reportIdToDate[cr.id]"></MonthEntry>
              </td>
              <td class="align-self-center pl-0 pt-3">
                <v-tooltip location="bottom" max-width="600px">
                  <template #activator="{ props }">
                    <v-btn
                      icon
                      variant="text"
                      size="x-small"
                      v-show="index > 0"
                      v-bind="props"
                      @click="
                        reportIdToDate[cr.id] =
                          reportIdToDate[counterReportsOrdered[index - 1].id]
                      "
                    >
                      <v-icon size="large" color="lighterIcons"
                        >far fa-copy</v-icon
                      >
                    </v-btn>
                  </template>
                  {{ $t("copy_tt") }}
                </v-tooltip>
              </td>
            </tr>
          </table>
        </v-col>
      </v-row>
    </v-card-text>
    <v-card-actions class="pb-4">
      <v-spacer></v-spacer>
      <v-btn
        @click="close"
        variant="flat"
        elevation="2"
        color="defaultButton"
        >{{ $t("close") }}</v-btn
      >
      <v-btn
        @click="apply"
        variant="flat"
        elevation="2"
        color="primary"
        :loading="loading"
      >
        {{ $t("apply") }}
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script>
import MonthEntry from "@/components/util/MonthEntry";
import SushiReportIndicator from "@/components/sushi/SushiReportIndicator";
import isEqual from "lodash/isEqual";

export default {
  name: "LastHarvestableMonthEntryWidget",

  components: { MonthEntry, SushiReportIndicator },

  props: {
    modelValue: { type: Object },
    counterReportsOrdered: { type: Array },
    loading: { type: Boolean, default: false },
    multipleCredentials: { type: Boolean, default: false },
  },

  data() {
    let reportIdToDate = {};
    if (this.modelValue) {
      reportIdToDate = { ...this.modelValue };
    } else {
      this.counterReportsOrdered.forEach((cr) => {
        reportIdToDate[cr.id] = cr.last_harvestable_month;
      });
    }
    return {
      reportIdToDate,
    };
  },

  methods: {
    close() {
      this.$emit("close");
    },
    apply() {
      Object.entries(this.reportIdToDate).forEach(([reportId, dateValue]) => {
        const reportData = { [reportId]: dateValue };
        this.$emit("apply", reportData);
      });
    },
  },

  watch: {
    modelValue: {
      handler: function (val) {
        if (val && !isEqual(val, this.reportIdToDate)) {
          this.reportIdToDate = { ...val };
        }
      },
      deep: true,
    },
    reportIdToDate: {
      handler: function (val) {
        this.$emit("update:modelValue", val);
      },
      deep: true,
    },
  },
};
</script>

<style lang="scss" scoped>
p {
  color: #00000090;
  font-size: 14px;
  &:first-child {
    padding-bottom: 15px;
  }
}
</style>
