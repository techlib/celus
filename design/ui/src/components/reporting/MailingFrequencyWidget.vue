<i18n lang="yaml" src="@/locales/reporting.yaml"></i18n>

<template>
  <div class="d-flex align-center ga-4" style="min-width: 16rem">
    <v-tooltip :text="$t('frequency_tt')" location="bottom" max-width="300">
      <template #activator="{ props }">
        <v-select
          v-model="selectedFrequency"
          :items="periods"
          item-value="value"
          item-title="label"
          hide-details
          class="flex-grow-0 pb-0 pt-0"
          density="compact"
          variant="plain"
          v-bind="props"
          min-width="120"
        ></v-select>
      </template>
    </v-tooltip>

    <v-tooltip
      :text="
        $t('number_of_periods_tt', {
          period: $t(`periods.${selectedFrequency}`),
        })
      "
      location="bottom"
    >
      <template #activator="{ props }">
        <v-select
          v-model="selectedNumberOfPeriods"
          :items="possibleNumberOfPeriods"
          hide-details
          variant="plain"
          v-bind="props"
          min-width="48"
          class="flex-grow-0 pb-0 pt-0"
          density="compact"
        ></v-select>
      </template>
    </v-tooltip>
    <span class="mt-1"> = {{ numberWithUnit }}</span>
  </div>
</template>

<script>
export default {
  props: {
    frequency: {
      type: String,
      required: false,
    },
    numberOfPeriods: {
      type: Number,
      required: false,
    },
    trendMode: {
      type: Boolean,
      required: false,
      default: false,
    },
  },

  emits: ["update:frequency", "update:numberOfPeriods", "update:mailing"],

  data() {
    return {
      selectedFrequency: this.frequency || "M",
      selectedNumberOfPeriods: this.numberOfPeriods || 12,

      periods: [
        { label: this.$t("frequency.M"), value: "M" },
        { label: this.$t("frequency.Q"), value: "Q" },
        { label: this.$t("frequency.H"), value: "H" },
        { label: this.$t("frequency.Y"), value: "Y" },
      ],
      periodRanges: {
        M: {
          min: 1,
          max: 36,
          default: 12,
          length: 1,
        },
        Q: {
          min: 1,
          max: 12,
          default: 4,
          length: 3,
        },
        H: {
          min: 1,
          max: 6,
          default: 2,
          length: 6,
        },
        Y: {
          min: 1,
          max: 3,
          default: 1,
          length: 12,
        },
      },
      periodToUnit: {
        M: "month",
        Q: "quarter",
        H: "half_year",
        Y: "year",
      },
    };
  },

  computed: {
    numberWithUnit() {
      return this.$tc(
        `period_unit.${this.periodToUnit[this.selectedFrequency]}`,
        this.selectedNumberOfPeriods,
        { count: this.selectedNumberOfPeriods },
      );
    },
    mailing() {
      return {
        frequency: this.selectedFrequency,
        numberOfPeriods: this.selectedNumberOfPeriods,
      };
    },
    possibleNumberOfPeriods() {
      // generate a list of possible number of periods based on the selected frequency
      // in case of a trend mode, the number of periods must be even
      const possiblePeriods = [];
      const diff = this.trendMode ? 2 : 1;
      let start = this.periodRanges[this.selectedFrequency].min;
      if (this.trendMode && start % 2 !== 0) {
        start += 1;
      }
      for (
        let i = start;
        i <= this.periodRanges[this.selectedFrequency].max;
        i += diff
      ) {
        possiblePeriods.push(i);
      }
      return possiblePeriods;
    },
  },

  watch: {
    selectedFrequency: {
      handler(newVal, oldVal) {
        // recompute between the old and new frequency based on the length of the period
        const oldLength = this.periodRanges[oldVal].length;
        const newLength = this.periodRanges[newVal].length;
        this.selectedNumberOfPeriods = Math.round(
          (this.selectedNumberOfPeriods * oldLength) / newLength,
        );
        if (this.selectedNumberOfPeriods > this.periodRanges[newVal].max) {
          this.selectedNumberOfPeriods = this.periodRanges[newVal].max;
        }
        if (
          !this.possibleNumberOfPeriods.includes(this.selectedNumberOfPeriods)
        ) {
          // if the selected number of periods is not in the possible list,
          // set it to the first possible number of periods
          this.selectedNumberOfPeriods = this.possibleNumberOfPeriods[0];
        }
        this.$emit("update:frequency", newVal);
        this.$emit("update:numberOfPeriods", this.selectedNumberOfPeriods);
      },
    },
    selectedNumberOfPeriods: {
      handler(newVal) {
        this.$emit("update:numberOfPeriods", newVal);
      },
    },
    mailing: {
      handler(newVal) {
        this.$emit("update:mailing", newVal);
      },
    },
  },
};
</script>

<style scoped lang="scss">
.no-label1 {
  .v-field__append-inner {
    padding-top: 0 !important;
  }
}
</style>
