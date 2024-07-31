<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml" src="@/locales/dialog.yaml"></i18n>

<i18n lang="yaml">
en:
  select_date_range: Select date range
  tooltip: Click to change the global date range
cs:
  select_date_range: Vyberte rozmezí dat
  tooltip: Kliknutím změníte globální nastavení zobrazovaného rozmezí dat
</i18n>

<template>
  <v-container ml-3>
    <v-row align="center">
      <v-col cols="auto" class="pa-0" shrink>
        <span :class="inputLikeLabel ? 'input-like' : 'sc'">
          {{ $t("labels.date_range") }} </span
        ><span v-if="!inputLikeLabel">:</span>
      </v-col>
      <v-col
        cols="auto"
        class="py-0"
        id="date-range-selector"
        :style="
          highlight
            ? {
                'background-color': 'rgba(255, 255, 0, .15)',
                border: 'solid 4px orange',
              }
            : { border: 'solid 4px transparent' }
        "
      >
        <v-tooltip bottom>
          <template v-slot:activator="{ on }">
            <div
              @click="showDialog = true"
              class="clickable align-center d-flex"
              v-on="on"
            >
              <v-container>
                <v-row>{{ rangeName }}</v-row>
                <v-row class="small subdued">
                  <DateRangeText :start="start" :end="end" />
                </v-row>

                <v-dialog v-model="showDialog" max-width="640px">
                  <v-card>
                    <v-card-title
                      class="d-flex justify-space-between align-center"
                    >
                      <span>{{ $t("select_date_range") }}</span>
                      <span style="max-width: 12rem">
                        <v-select
                          :items="months"
                          v-model="fyStart"
                          :label="$t('labels.fiscal_year_start_month')"
                          dense
                          outlined
                          class="caption"
                          hide-details
                        />
                      </span>
                    </v-card-title>
                    <v-divider></v-divider>
                    <v-card-text class="pt-4">
                      <DateRangeSelector />
                    </v-card-text>
                    <v-card-actions>
                      <v-spacer></v-spacer>
                      <v-btn color="primary" text @click="showDialog = false">{{
                        $t("close")
                      }}</v-btn>
                    </v-card-actions>
                  </v-card>
                </v-dialog>
              </v-container>
              <div class="pl-2"><v-icon>fa-caret-down</v-icon></div>
            </div>
          </template>
          <div>
            <span v-text="$t('tooltip')"></span>
          </div>
        </v-tooltip>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { mapActions, mapGetters, mapState } from "vuex";
import DateRangeSelector from "./DateRangeSelector";
import DateRangeText from "@/components/util/DateRangeText";

export default {
  name: "SelectedDateRangeWidget",
  components: { DateRangeText, DateRangeSelector },
  props: {
    inputLikeLabel: { default: false, type: Boolean },
  },
  data() {
    return {
      showDialog: false,
    };
  },
  computed: {
    ...mapState({
      start: "dateRangeStart",
      end: "dateRangeEnd",
      highlight: "highlightDateRangeSelector",
      fiscalYearStart: "fiscalYearStart",
      dateRangeName: "dateRangeName",
      defaultDateRangeName: "defaultDateRangeName",
      defaultFYDateRangeName: "defaultFYDateRangeName",
    }),
    ...mapGetters({
      rangeObject: "selectedDateRange",
    }),
    rangeName() {
      return this.$i18n.t(this.rangeObject.name);
    },
    fyStart: {
      get() {
        return this.fiscalYearStart;
      },
      set(value) {
        this.setFiscalYearStart(value);
      },
    },
    months() {
      let out = [];
      for (let i = 0; i < 12; i++) {
        let d = new Date(2020, i, 1);
        const month = d.toLocaleString("en", { month: "long" });
        out.push({ text: month, value: i });
      }
      return out;
    },
  },
  methods: {
    ...mapActions({
      setFiscalYearStart: "setFiscalYearStart",
      changeDateRangeObject: "changeDateRangeObject",
    }),
  },
  watch: {
    fiscalYearStart: {
      // this ensures that when the fiscal year start changes, the date range is updated
      // throughout the whole application
      handler(newValue, oldValue) {
        if (newValue !== oldValue) {
          if (oldValue === 0) {
            // this is the first time the fiscal year start is set
            // we need to set the date range to the current + previous fiscal year
            this.changeDateRangeObject(this.defaultFYDateRangeName);
          } else if (newValue === 0 && this.dateRangeName.includes("fy")) {
            // when the fiscal year start is set to 0, we will hide the
            // FY related date ranges, so we need to select the default
            this.changeDateRangeObject(this.defaultDateRangeName);
          } else {
            // in all other cases, we just make sure the date range is updated
            // by refreshing the current date range
            this.changeDateRangeObject(this.dateRangeName);
          }
        }
      },
      immediate: true,
    },
  },
};
</script>

<style scoped lang="scss">
.small {
  font-size: 0.875rem;
}

span.input-like {
  color: rgba(0, 0, 0, 0.6);
  font-size: 0.75rem;
}

.clickable {
  cursor: pointer;
}
</style>
