<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<i18n lang="yaml">
en:
  select_dates_text: "Select date range to harvest:"
  select_dates_text_test_note: "It is ok to use a longer time period for verification. The harvest will run from the most recent month to the oldest and will stop immediately if an authentication error occurs."
  there_were_errors: "It was not possible to start harvesting due to the following error:| It was not possible to start harvesting due to the following errors:"
  check_credentials: Please check selection of credentials after closing this dialog. Broken credentials will be automatically unselected.
  start_harvesting: "Nothing to harvest | Start {count} download | Start {count} downloads"
  nothing_to_harvest: Nothing to harvest
  no_problem_closing_dialog: Feel free to close this dialog. The harvesting will continue in the background and you can review the progress on the {harvest_link}
  harvest_page: SUSHI harvests page
  reharvest_mode: Reharvest mode
  reharvest_mode_tt: Switch on to delete existing data before harvesting

cs:
  select_dates_text: "Vyberte rozsah měsíců pro stažení:"
  select_dates_text_test_note: "Pro ověření je možné použít delší časové období. Stahování bude probíhat od nejnovějšího měsíce k nejstaršímu a okamžitě se zastaví, pokud dojde k chybě autentizace."
  there_were_errors: "Nebylo možné zahájit harvesting kvůli následující chybě: | Nebylo možné zahájit harvesting kvůli následujícím chybám: | Nebylo možné zahájit harvesting kvůli následujícím chybám:"
  check_credentials: Po uzavření dialogu zkontrolujte prosím výběr přihlašovacích údajů. Označení nefunkčních bude automaticky zrušeno.
  start_harvesting: "Začít {count} stahování | Začít {count} stahování | Začít {count} stahování"
  nothing_to_harvest: Není co stahovat
  no_problem_closing_dialog: Tento dialog můžete bezpečně zavřít. Stahování bude pokračovat na pozadí. Vrátit se k němu můžete na {harvest_link}
  harvest_page: stránce Stahování SUSHI
  reharvest_mode: Reharvestovací mód
  reharvest_mode_tt: Zapněte pro smazání existujících dat před stahováním
</i18n>

<template>
  <v-container fluid class="pb-0">
    <v-row v-if="!started" class="align-center">
      <v-col cols="12" md="auto">{{ $t("select_dates_text") }}</v-col>
      <v-col cols="2">
        <DatePicker
          :disabled="started"
          v-model="startDate"
          :max-date="EndDateText"
        >
          <template v-slot:activator="{ props }">
            <v-text-field
              hide-details="auto"
              v-model="StartTextField"
              :label="$t('title_fields.start_date')"
              prepend-icon="fa fa-calendar"
              readonly
              v-bind="props"
            ></v-text-field>
          </template>
        </DatePicker>
      </v-col>
      <v-col cols="2">
        <DatePicker
          :disabled="started"
          v-model="endDate"
          :min-date="StartDateText"
          :max-date="new Date()"
        >
          <template v-slot:activator="{ props }">
            <v-text-field
              hide-details="auto"
              v-model="EndTextField"
              :label="$t('title_fields.end_date')"
              prepend-icon="fa fa-calendar"
              readonly
              v-bind="props"
            ></v-text-field>
          </template>
        </DatePicker>
      </v-col>
      <v-col cols="auto">
        <v-btn
          @click="startHarvest()"
          color="primary"
          width="100%"
          :disabled="!totalReportCount || !slotsReady || slotsFree === 0"
        >
          {{
            slotsFree === 0
              ? $t("nothing_to_harvest")
              : $tc("start_harvesting", slotsFree)
          }}
        </v-btn>
      </v-col>
      <v-spacer />
      <v-col cols="auto" v-if="!test && showReharvest">
        <v-tooltip location="bottom" max-width="600px">
          <template #activator="{ props }">
            <v-switch
              hide-details="auto"
              v-bind="props"
              v-model="reharvestMode"
              color="primary"
              density="compact"
              :label="$t('reharvest_mode')"
            ></v-switch>
          </template>
          {{ $t("reharvest_mode_tt") }}
        </v-tooltip>
      </v-col>
    </v-row>
    <v-row v-if="test">
      <v-col>
        <v-alert type="info" variant="outlined">
          <div v-html="$t('select_dates_text_test_note')"></div>
        </v-alert>
      </v-col>
    </v-row>
    <v-row v-if="!started">
      <v-col>
        <div v-if="startDate && endDate">
          <SushiHarvestedSlotsWidget
            :credentials="credentials"
            :start-date="PickerTextStart(startDate)"
            :end-date="PickerTextStart(endDate)"
            ref="slotWidget"
            v-model="slotsReady"
            :reharvest="reharvestMode"
          ></SushiHarvestedSlotsWidget>
        </div>
      </v-col>
    </v-row>
    <v-row v-else-if="error">
      <v-col>
        <v-alert type="error" variant="outlined">
          <p>{{ $tc("there_were_errors", errors.length) }}</p>
          <ul>
            <li v-for="(error, index) in errors" :key="index">
              <strong>
                {{ error.organization.name }}, {{ error.platform.short_name }},
                COUNTER {{ error.counter_version }}</strong
              >:
              {{ error.errorMessage }}
            </li>
          </ul>
          <p class="pt-6">{{ $t("check_credentials") }}</p>
        </v-alert>
      </v-col>
    </v-row>
    <template v-else>
      <v-row>
        <SushiFetchIntentionsListWidget
          :harvest-id="harvestId"
          ref="intentionsList"
        ></SushiFetchIntentionsListWidget>
      </v-row>
      <v-row>
        <v-col>
          <v-alert type="info" variant="tonal" density="compact" class="me-3">
            <i18n-t keypath="no_problem_closing_dialog">
              <template #harvest_link>
                <router-link :to="{ name: 'harvests' }">
                  {{ $t("harvest_page") }}
                </router-link>
              </template>
            </i18n-t>
          </v-alert>
        </v-col>
      </v-row>
    </template>
    <v-dialog
      v-if="showDeleteDialog"
      v-model="showDeleteDialog"
      max-width="1100px"
    >
      <ImportBatchesDeleteConfirm
        :import-batch-slices="importBatchSlicesToDelete"
        :intention-slices="intentionSlicesToDelete"
        @cancel="showDeleteDialog = false"
        @deleted="dataDeleted"
        reharvest
      ></ImportBatchesDeleteConfirm>
    </v-dialog>
  </v-container>
</template>

<script>
import { mapActions } from "vuex";
import axios from "axios";
import {
  lastFinishedMonth,
  lastFinishedMonthDate,
  monthFirstDay,
  monthLastDay,
  ymDateFormat,
  ymDateParse,
} from "@/libs/dates";
import SushiFetchIntentionsListWidget from "@/components/sushi/SushiFetchIntentionsListWidget";
import SushiHarvestedSlotsWidget from "@/components/sushi/SushiHarvestedSlotsWidget";
import ImportBatchesDeleteConfirm from "@/components/ImportBatchesDeleteConfirm.vue";
import addMonths from "date-fns/addMonths";
import DatePicker from "@/components/DatePicker.vue";
import { mapState } from "vuex";
export default {
  name: "HarvestSelectedWidget",

  components: {
    ImportBatchesDeleteConfirm,
    SushiHarvestedSlotsWidget,
    SushiFetchIntentionsListWidget,
    DatePicker,
  },

  props: {
    credentials: { required: true, type: Array },
    retryInterval: { default: 1000, type: Number },
    showOrganization: { default: false, type: Boolean },
    showPlatform: { default: false, type: Boolean },
    // is this dialog used for testing? Influences wording and the selection of months
    test: { default: false, type: Boolean },
    showReharvest: { default: true, type: Boolean },
  },

  data() {
    return {
      harvestId: null,
      started: false,
      startDateMenu: null,
      reharvestMode: false,
      endDateMenu: null,
      error: null,
      slotsReady: false,
      showDeleteDialog: false,
    };
  },

  computed: {
    ...mapState({
      dateRangeName: "dateRangeName",
      startRaw: "dateRangeStart",
      endRaw: "dateRangeEnd",
    }),

    startDate: {
      get() {
        return {
          month: this.startRaw.getMonth(),
          year: this.startRaw.getFullYear(),
        };
      },
      set(value) {
        if (value && typeof value === "object" && "month" in value) {
          const day = value.day || 1;
          this.setDateRangeStart(new Date(value.year, value.month, day));
        } else if (typeof value === "string") {
          let date = ymDateParse(value);
          this.setDateRangeStart(date);
        } else {
          this.setDateRangeStart(value);
        }
      },
    },
    endDate: {
      get() {
        if (this.endRaw) {
          return {
            month: this.endRaw.getMonth(),
            year: this.endRaw.getFullYear(),
          };
        } else {
          return {
            month: new Date().getMonth(),
            year: new Date().getFullYear(),
          };
        }
      },
      set(value) {
        if ("month" in value) {
          this.setDateRangeEnd(new Date(value.year, value.month));
        } else {
          this.setDateRangeEnd(value);
        }
      },
    },
    StartDateText() {
      if (typeof this.startDate === "string" || this.startDate === null) {
        return new Date(this.startDate);
      } else {
        return new Date(this.startDate.year, this.startDate.month);
      }
    },
    StartTextField() {
      if (
        typeof this.startDate === "object" &&
        this.startDate !== null &&
        "month" in this.startDate
      ) {
        return `${this.startDate.year}-${
          this.startDate.month <= 8
            ? `0${this.startDate.month + 1}`
            : this.startDate.month + 1
        }`;
      } else {
        return this.startDate;
      }
    },
    EndDateText() {
      if (typeof this.endDate === "string" || this.endDate === null) {
        return new Date(this.endDate);
      } else {
        return new Date(this.endDate.year, this.endDate.month);
      }
    },
    EndTextField() {
      if (
        typeof this.endDate === "object" &&
        this.startDate !== null &&
        "month" in this.endDate
      ) {
        return `${this.endDate.year}-${
          this.endDate.month <= 8
            ? `0${this.endDate.month + 1}`
            : this.endDate.month + 1
        }`;
      } else {
        return this.endDate;
      }
    },
    totalReportCount() {
      return this.credentials
        .map(
          (cred) =>
            cred.counter_reports_long.filter((item) => !item.broken).length,
        )
        .reduce((a, b) => a + b, 0);
    },
    errors() {
      if (this.error !== null) {
        let brokenCredentialIds = new Set();
        for (let key of Object.keys(this.error.response.data)) {
          brokenCredentialIds.add(Number.parseInt(key));
        }
        let brokenCredentials = this.credentials.filter((item) =>
          brokenCredentialIds.has(item.pk),
        );
        brokenCredentials.forEach((item) => {
          item.errorMessage = this.error.response.data[item.pk];
        });
        return brokenCredentials;
      }
      return [];
    },
    monthsToCover() {
      let start = null;
      if ("month" in this.startDate && typeof this.startDate === "object") {
        start = ymDateParse(
          new Date(this.startDate.year, this.startDate.month),
        );
      } else {
        start = ymDateParse(new Date(this.startDate));
      }
      let months = [start];
      if (this.test) {
        return months;
      }
      let endMonth = null;
      if ("month" in this.endDate && typeof this.endDate === "object") {
        endMonth = ymDateParse(new Date(this.endDate.year, this.endDate.month));
      } else {
        endMonth = ymDateParse(new Date(this.endDate));
      }
      while (start < endMonth) {
        start = addMonths(start, 1);
        months.push(start);
      }
      return months;
    },
    monthsToCoverCount() {
      return this.monthsToCover.length;
    },
    slotsFree() {
      if (this.slotsReady && this.$refs.slotWidget) {
        return this.$refs.slotWidget.slotsFree;
      }
      return 0;
    },
    importBatchSlicesToDelete() {
      // list of import batches to delete - used by ImportBatchesDeleteConfirm
      let out = [];
      if (this.reharvestMode) {
        for (let rec of this.$refs.slotWidget.tableData) {
          let months = Object.entries(rec.months)
            .filter(([month, source]) => source === "rh-ok")
            .map(([month, source]) => month + "-01");
          if (months.length > 0) {
            out.push({
              platform: rec.cred.platform.pk,
              organization: rec.cred.organization.pk,
              report_type: rec.rt.report_type,
              months: months,
            });
          }
        }
      }
      return out;
    },
    intentionSlicesToDelete() {
      // list of intentions to delete - used by ImportBatchesDeleteConfirm
      // I am not completely sure why we need this when the intentions
      // are deleted together with the import batches,
      // but I copied it from SushiCredentialsDataDialog.vue
      let out = [];
      if (this.reharvestMode) {
        for (let rec of this.$refs.slotWidget.tableData) {
          for (let [month, source] of Object.entries(rec.months)) {
            if (source === "rh-ok") {
              out.push({
                credentials: rec.cred.pk,
                counter_report: rec.rt.id,
                start_date: month + "-01",
              });
            }
          }
        }
      }
      return out;
    },
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
      setDateRangeStart: "changeDateRangeStart",
      setDateRangeEnd: "changeDateRangeEnd",
    }),
    PickerTextStart(value) {
      if (value) {
        if (typeof value === "object" && "month" in value) {
          return `${value.year}-${
            value.month <= 8 ? `0${value.month + 1}` : value.month + 1
          }`;
        } else {
          return value;
        }
      }
    },
    async startHarvest() {
      // if in reharvest mode, delete existing data first
      if (
        this.reharvestMode &&
        (this.importBatchSlicesToDelete.length ||
          this.intentionSlicesToDelete.length)
      ) {
        // if we are in reharvest mode, we cannot run createIntentions
        // until all the data is deleted
        this.showDeleteDialog = true;
        return;
      }
      // now create the intentions
      await this.createIntentions();
    },

    async createIntentions() {
      let intentions = [];

      for (let rec of this.$refs.slotWidget.tableData) {
        for (let [month, source] of Object.entries(rec.months)) {
          if (source === "" || source === "rh-ok") {
            let monthDate = ymDateParse(month);
            intentions.push({
              start_date: monthFirstDay(monthDate),
              end_date: monthLastDay(monthDate),
              credentials: rec.cred.pk,
              counter_report: rec.rt.id,
            });
          }
        }
      }
      this.started = true;

      try {
        let response = await axios.post(`/api/scheduler/harvest/`, {
          intentions: intentions,
        });
        this.harvestId = response.data.pk;
      } catch (error) {
        if (error.response?.status === 400 && error.response?.data) {
          this.error = error;
        } else {
          this.showSnackbar({
            content: "Error starting SUSHI harvest: " + error,
            color: "error",
          });
        }
      }
    },
    async dataDeleted() {
      this.showDeleteDialog = false;
      await this.$refs.slotWidget.fetchPresenceData();
      // we call startHarvest() again to make sure that no data is left
      await this.startHarvest();
    },
    allowedStartMonths(value) {
      let end = this.endDate;
      if (end) {
        return value <= end && value > "2010";
      }
      return value < ymDateFormat(new Date()) && value > "2010";
    },
    allowedEndMonths(value) {
      let now = ymDateFormat(new Date());
      let start = this.startDate;
      if (start) {
        return start <= value && value < now;
      }
      return value < now;
    },
    clean() {
      this.started = false;
      if (this.$refs.intentionsList) {
        this.$refs.intentionsList.stop();
      }
    },
  },

  mounted() {
    if (this.startDate === null) {
      this.startDate = ymDateFormat(addMonths(lastFinishedMonthDate(), -11));
    }
    if (this.endDate === null) {
      this.endDate = lastFinishedMonth();
    }
  },
};
</script>

<style lang="scss" scoped>
.text_date {
  font-size: 14px;
  color: rgba(0, 0, 0, 0.6);
}
</style>
