<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml">
en:
  select_dates_text:
    Select date range for SUSHI credentials test. A shorter period usually takes
    less time to process, so using only one month is advisable.
  credentials_count: Number of credentials to test
  report_count: Number of reports to test

cs:
  select_dates_text:
    Vyberte rozsah měsíců pro test přihlašovacích údajů. Kratší období je většinou
    rychleji zpracováno, takže je vhodné vybrat jen jeden měsíc.
  credentials_count: Počet přihlašovacích údajů k otestování
  report_count: Počet reportů k otestování
</i18n>

<template>
  <v-container class="pb-0">
    <v-row>
      <v-col>{{ $t("select_dates_text") }}</v-col>
    </v-row>
    <v-row align="center">
      <v-col cols="6" md="4">
        <v-menu
          v-model="startDateMenu"
          :close-on-content-click="false"
          :nudge-right="40"
          transition="scale-transition"
          offset-y
          min-width="290px"
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
      <v-col cols="6" md="4" lg="3" v-if="!started">
        <v-btn
          @click="createAttempts()"
          v-text="$t('actions.start_test')"
          color="primary"
          class=""
          width="100%"
        ></v-btn>
      </v-col>
    </v-row>

    <v-row v-if="!started">
      <v-col>
        <strong>{{ $t("credentials_count") }}</strong
        >: {{ credentials.length }}<br />
        <strong>{{ $t("report_count") }}</strong
        >: {{ totalReportCount }}
      </v-col>
    </v-row>

    <v-row v-else no-gutters>
      <v-expansion-panels>
        <SushiCredentialsStatusWidget
          v-for="attemptId in attemptIds"
          :attempt-id="attemptId"
          :key="attemptId"
          ref="attemptStatus"
          :retryInterval="retryInterval"
          :show-organization="showOrganization"
          :show-platform="showPlatform"
        >
        </SushiCredentialsStatusWidget>
      </v-expansion-panels>
    </v-row>
  </v-container>
</template>

<script>
import { mapActions } from "vuex";
import axios from "axios";
import { ymDateFormat } from "@/libs/dates";
import SushiCredentialsStatusWidget from "./SushiCredentialsStatusWidget";
import addMonths from "date-fns/addMonths";

export default {
  name: "SushiCredentialsTestWidget",

  components: { SushiCredentialsStatusWidget },

  props: {
    credentials: { required: true, type: Array },
    retryInterval: { default: 1000, type: Number },
    showOrganization: { default: false, type: Boolean },
    showPlatform: { default: false, type: Boolean },
  },

  data() {
    return {
      attemptIds: [], //11757, 11758],
      startDate: null,
      endDate: null,
      started: false,
      startDateMenu: null,
      endDateMenu: null,
    };
  },

  computed: {
    totalReportCount() {
      let total = 0;
      for (let cred of this.credentials) {
        total += cred.counter_reports.length;
      }
      return total;
    },
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    async createAttempts() {
      for (let cred of this.credentials) {
        for (let rt of cred.counter_reports) {
          await this.createAttempt(cred, rt);
        }
        this.started = true;
      }
    },
    async createAttempt(credentials, reportType) {
      try {
        let response = await axios.post(`/api/sushi-fetch-attempt/`, {
          start_date: this.startDate + "-01",
          end_date: this.endDate + "-01",
          credentials: credentials.pk,
          counter_report: reportType,
        });
        this.attemptIds.push(response.data.pk);
      } catch (error) {
        this.showSnackbar({
          content: "Error starting SUSHI test: " + error,
          color: "error",
        });
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
      if (this.$refs.attemptStatus) {
        for (let comp of this.$refs.attemptStatus) {
          comp.stop();
        }
      }
      this.attemptIds = [];
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
