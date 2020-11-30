<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml">
en:
  select_dates_text: Select date range for manual SUSHI harvesting.
  select_dates_text_test:
    Select date range for SUSHI credentials test. A shorter period usually takes
    less time to process, so using only one month is advisable.
  credentials_count: Number of credentials to harvest
  credentials_count_test: Number of credentials to test
  report_count: Number of reports to harvest
  report_count_test: Number of reports to test
  broken_report_count: Number of broken reports (not harvested)
  broken_reports_tooltip:
    These reports have been marked as broken by Celus and will not be harvested. Switch them off
    by editing corresponding credentials.
  there_were_errors: " | It was not possible to start harvesting due to the following error: | It was not possible to start harvesting due to the following errors:"
  check_credentials: Please check selection of credentials after closing this dialog. Broken credentials will be automatically unselected.

cs:
  select_dates_text: Vyberte rozsah měsíců pro manuální stahování SUSHI.
  select_dates_text_test:
    Vyberte rozsah měsíců pro test přihlašovacích údajů. Kratší období je většinou
    rychleji zpracováno, takže je vhodné vybrat jen jeden měsíc.
  credentials_count: Počet přihlašovacích údajů ke stažení
  credentials_count_test: Počet přihlašovacích údajů k otestování
  report_count: Počet reportů ke stažení
  report_count_text: Počet reportů k otestování
  broken_report_count: Počet nefunkčních reportů (nebudou stahovány)
  broken_reports_tooltip:
    Celus tyto reporty označil za nefunkční a nebudou staženy. Vypněte je editací
    příslušných přihlašovacích údajů.
  there_were_errors: "Nebylo možné zahájit harvesting kvůli následující chybě: | Nebylo možné zahájit harvesting kvůli následujícím chybám: | Nebylo možné zahájit harvesting kvůli následujícím chybám:"
  check_credentials: Po uzavření dialogu zkontrolujte prosím výběr přihlašovacích údajů. Označení nefunkčních bude automaticky zrušeno.
</i18n>

<template>
  <v-container fluid class="pb-0">
    <v-row v-if="!started">
      <v-col
        v-text="test ? $t('select_dates_text_test') : $t('select_dates_text')"
      ></v-col>
    </v-row>
    <v-row align="center" v-if="!started">
      <v-col cols="6" md="4">
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
              :label="$t('title_fields.start_date')"
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
      <v-col cols="6" md="4">
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
      <v-col cols="6" md="4" lg="3">
        <v-btn
          @click="createIntentions()"
          v-text="
            test ? $t('actions.start_test') : $t('actions.start_harvesting')
          "
          color="primary"
          class=""
          width="100%"
          :disabled="!totalReportCount"
        ></v-btn>
      </v-col>
    </v-row>

    <v-row v-if="!started">
      <v-col>
        <strong
          v-text="test ? $t('credentials_count_test') : $t('credentials_count')"
        ></strong
        >: {{ credentials.length }}<br />
        <strong>{{ $t("report_count") }}</strong
        >:
        <span :class="totalReportCount == 0 ? 'error--text' : ''">{{
          totalReportCount
        }}</span>
        <br />
        <strong>{{ $t("broken_report_count") }}</strong
        >: {{ brokenReportCount }}
        <v-tooltip v-if="brokenReportCount" bottom max-width="400">
          <template #activator="{ on }">
            <v-icon v-on="on" color="warning" small>fa-info-circle</v-icon>
          </template>
          {{ $t("broken_reports_tooltip") }}
        </v-tooltip>
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
import { ymDateFormat, ymFirstDay, ymLastDay } from "@/libs/dates";
import addMonths from "date-fns/addMonths";
import HarvestsTable from "@/components/HarvestsTable";
import SushiFetchIntentionsListWidget from "@/components/sushi/SushiFetchIntentionsListWidget";

export default {
  name: "SushiCredentialsTestWidget",

  components: {
    SushiFetchIntentionsListWidget,
    HarvestsTable,
  },

  props: {
    credentials: { required: true, type: Array },
    retryInterval: { default: 1000, type: Number },
    showOrganization: { default: false, type: Boolean },
    showPlatform: { default: false, type: Boolean },
    test: { default: false, type: Boolean }, // is this dialog used for testing? Influences wording.
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
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    async createIntentions() {
      let intentions = [];
      let startDate = ymFirstDay(this.startDate);
      let endDate = ymLastDay(this.endDate);

      for (let cred of this.credentials) {
        for (let rt of cred.counter_reports_long) {
          if (!rt.broken) {
            intentions.push({
              start_date: startDate,
              end_date: endDate,
              credentials: cred.pk,
              counter_report: rt.id,
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
        return value <= end;
      }
      return value < ymDateFormat(new Date());
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
