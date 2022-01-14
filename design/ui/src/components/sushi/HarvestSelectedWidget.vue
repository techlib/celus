<i18n lang="yaml" src="../../locales/common.yaml"></i18n>
<i18n lang="yaml">
en:
  select_dates_text: "Select date range to harvest:"
  select_dates_text_test: "Select the month for SUSHI credentials test:"
  select_dates_text_test_note:
    "<strong>Note</strong>: we use one month for testing to make it as fast as possible.
    If you want to download data for a longer period, use the 'Harvest selected' button on the SUSHI management page."
  there_were_errors: " | It was not possible to start harvesting due to the following error: | It was not possible to start harvesting due to the following errors:"
  check_credentials: Please check selection of credentials after closing this dialog. Broken credentials will be automatically unselected.
  test_date: Month to test on
  start_harvesting: "Nothing to harvest | Start {count} download | Start {count} downloads"
  nothing_to_harvest: Nothing to harvest

cs:
  select_dates_text: "Vyberte rozsah měsíců pro stažení:"
  select_dates_text_test: "Vyberte měsíc pro otestování přihlašovacích údajů:"
  select_dates_text_test_note:
    "<strong>Poznámka</strong>: pro co nejrychlejší otestování stahujeme data pouze za jeden měsíc. Pokud chcete
    stáhnout data za delší období, použijte tlačítko 'Stáhni označené' na stránce správy SUSHI."
  there_were_errors: "Nebylo možné zahájit harvesting kvůli následující chybě: | Nebylo možné zahájit harvesting kvůli následujícím chybám: | Nebylo možné zahájit harvesting kvůli následujícím chybám:"
  check_credentials: Po uzavření dialogu zkontrolujte prosím výběr přihlašovacích údajů. Označení nefunkčních bude automaticky zrušeno.
  test_date: Testovaný měsíc
  start_harvesting: "Začít {count} stahování | Začít {count} stahování | Začít {count} stahování"
  nothing_to_harvest: Není co stahovat
</i18n>

<template>
  <v-container fluid class="pb-0">
    <v-row v-if="!started" class="align-center">
      <v-col
        v-html="test ? $t('select_dates_text_test') : $t('select_dates_text')"
        cols="12"
        md="auto"
      ></v-col>
      <v-col cols="auto">
        <v-menu
          v-model="startDateMenu"
          :close-on-content-click="false"
          :nudge-right="40"
          transition="scale-transition"
          offset-y
          min-width="290px"
          :disabled="started"
        >
          <template v-slot:activator="{ on }">
            <v-text-field
              v-model="startDate"
              :label="test ? $t('test_date') : $t('title_fields.start_date')"
              prepend-icon="fa-calendar"
              readonly
              v-on="on"
            ></v-text-field>
          </template>
          <v-date-picker
            v-model="startDate"
            type="month"
            no-title
            :locale="$i18n.locale"
            :allowed-dates="allowedStartMonths"
          ></v-date-picker>
        </v-menu>
      </v-col>
      <v-col cols="auto" v-if="!test">
        <v-menu
          v-model="endDateMenu"
          :close-on-content-click="false"
          :nudge-right="40"
          transition="scale-transition"
          offset-y
          min-width="290px"
          :disabled="started"
        >
          <template v-slot:activator="{ on }">
            <v-text-field
              v-model="endDate"
              :label="$t('title_fields.end_date')"
              prepend-icon="fa-calendar"
              readonly
              v-on="on"
            ></v-text-field>
          </template>
          <v-date-picker
            v-model="endDate"
            type="month"
            no-title
            :locale="$i18n.locale"
            :allowed-dates="allowedEndMonths"
          ></v-date-picker>
        </v-menu>
      </v-col>
      <v-col cols="auto">
        <v-btn
          @click="createIntentions()"
          v-text="
            slotsFree === 0
              ? $t('nothing_to_harvest')
              : test
              ? $t('actions.start_test')
              : $tc('start_harvesting', slotsFree)
          "
          color="primary"
          class=""
          width="100%"
          :disabled="!totalReportCount || !slotsReady || slotsFree === 0"
        ></v-btn>
      </v-col>
    </v-row>
    <v-row v-if="test">
      <v-col>
        <div v-html="$t('select_dates_text_test_note')"></div>
      </v-col>
    </v-row>

    <v-row v-if="!started">
      <v-col>
        <div v-if="startDate && endDate">
          <SushiHarvestedSlotsWidget
            :credentials="credentials"
            :start-date="startDate"
            :end-date="test ? startDate : endDate"
            ref="slotWidget"
            :ready.sync="slotsReady"
          />
        </div>
      </v-col>
    </v-row>

    <v-row v-else-if="error">
      <v-col>
        <v-alert type="error" outlined>
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

    <v-row v-else no-gutters>
      <SushiFetchIntentionsListWidget
        :harvest-id="harvestId"
        ref="intentionsList"
      />
    </v-row>
  </v-container>
</template>

<script>
import { mapActions } from "vuex";
import axios from "axios";
import {
  monthFirstDay,
  monthLastDay,
  ymDateFormat,
  ymDateParse,
} from "@/libs/dates";
import addMonths from "date-fns/addMonths";
import SushiFetchIntentionsListWidget from "@/components/sushi/SushiFetchIntentionsListWidget";
import SushiHarvestedSlotsWidget from "@/components/sushi/SushiHarvestedSlotsWidget";

export default {
  name: "HarvestSelectedWidget",

  components: {
    SushiHarvestedSlotsWidget,
    SushiFetchIntentionsListWidget,
  },

  props: {
    credentials: { required: true, type: Array },
    retryInterval: { default: 1000, type: Number },
    showOrganization: { default: false, type: Boolean },
    showPlatform: { default: false, type: Boolean },
    // is this dialog used for testing? Influences wording and the selection of months
    test: { default: false, type: Boolean },
  },

  data() {
    return {
      harvestId: null,
      startDate: null,
      endDate: null,
      started: false,
      startDateMenu: null,
      endDateMenu: null,
      error: null,
      slotsReady: false,
    };
  },

  computed: {
    totalReportCount() {
      return this.credentials
        .map(
          (cred) =>
            cred.counter_reports_long.filter((item) => !item.broken).length
        )
        .reduce((a, b) => a + b);
    },
    brokenReportCount() {
      return this.credentials
        .map(
          (cred) =>
            cred.counter_reports_long.filter((item) => item.broken).length
        )
        .reduce((a, b) => a + b);
    },
    errors() {
      if (this.error !== null) {
        let brokenCredentialIds = new Set();
        for (let key of Object.keys(this.error.response.data)) {
          brokenCredentialIds.add(Number.parseInt(key));
        }
        let brokenCredentials = this.credentials.filter((item) =>
          brokenCredentialIds.has(item.pk)
        );
        brokenCredentials.forEach((item) => {
          item.errorMessage = this.error.response.data[item.pk];
        });
        return brokenCredentials;
      }
      return [];
    },
    monthsToCover() {
      let start = ymDateParse(this.startDate);
      let months = [start];
      if (this.test) {
        return months;
      }
      const endMonth = ymDateParse(this.endDate);
      while (start < endMonth) {
        start = addMonths(start, 1);
        months.push(start);
      }
      return months;
    },
    monthsToCoverCount() {
      return this.monthsToCover.length;
    },
    totalAttemptCount() {
      return this.totalReportCount * this.monthsToCoverCount;
    },
    slotsFree() {
      if (this.slotsReady && this.$refs.slotWidget) {
        return this.$refs.slotWidget.slotsFree;
      }
      return 0;
    },
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    async createIntentions() {
      let intentions = [];

      for (let rec of this.$refs.slotWidget.tableData) {
        for (let [month, source] of Object.entries(rec.months)) {
          if (source === "") {
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
        if (error.response.status === 400 && error.response.data) {
          this.error = error;
        } else {
          this.showSnackbar({
            content: "Error starting SUSHI test: " + error,
            color: "error",
          });
        }
      }
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
      this.startDate = ymDateFormat(addMonths(new Date(), -1));
    }
    if (this.endDate === null) {
      this.endDate = this.startDate;
    }
  },
};
</script>

<style scoped></style>
