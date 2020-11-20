<i18n lang="yaml" src="../../locales/common.yaml"></i18n>
<i18n lang="yaml">
en:
  cleanup:
    older_than: Remove attempts older than
    older_date: Date
    older_time: Time
    button: Delete
    done: "No need to delete any attempts.|{n} record was successfully deleted.|{n} records were successfully deleted."
    text: "There are no attempts to delete.|Are you sure that you want to delete {n} unsuccessful attempt?|Are you sure that you want to delete {n} unsuccessful attempts?"

cs:
  cleanup:
    older_than: Smazat pokusy starší než
    older_date: Datum
    older_time: Čas
    button: Vymazat
    done: "Nebylo potřeba mazat pokusy.|{n} pokus byl úspěšně vymazán.|{n} pokusy byly úspěšně vymazány.|{n} pokusů bylo úspěšně vymazáno."
    text: "Žádný neúspěšný pokus nenalezen.|Určitě chcete smazat {n} neúspěšný pokus?|Určitě chcete smazat {n} neúspěšné pokusy?|Určitě chcete smazat {n} neúspěšných pokusů?"
</i18n>

<template>
  <v-container class="pa-0">
    <v-row>
      <v-col>{{ $t("cleanup.older_than") }}</v-col>
    </v-row>
    <v-row justify="center">
      <v-col>
        <v-menu
          v-model="olderThenDateMenu"
          :close-on-content-click="false"
          :nudge-right="40"
          transition="scale-transition"
          offset-y
          min-width="290px"
        >
          <template v-slot:activator="{ on }">
            <v-text-field
              v-model="olderThenDate"
              :label="$t('cleanup.older_date')"
              prepend-icon="fa-calendar"
              readonly
              v-on="on"
            ></v-text-field>
          </template>
          <v-date-picker
            v-model="olderThenDate"
            no-title
            :locale="$i18n.locale"
            @change="numberOfAttempsToCleanup"
          ></v-date-picker>
        </v-menu>
      </v-col>
      <v-col>
        <v-menu
          ref="timeMenu"
          v-model="olderThenTimeMenu"
          :close-on-content-click="false"
          :nudge-right="40"
          transition="scale-transition"
          offset-y
          min-width="290px"
          @input="
            (value) =>
              value &&
              $refs.timePicker &&
              ($refs.timePicker.selectingHour = true)
          "
        >
          <template v-slot:activator="{ on }">
            <v-text-field
              v-model="olderThenTime"
              :label="$t('cleanup.older_time')"
              prepend-icon="fa-clock"
              readonly
              v-on="on"
            ></v-text-field>
          </template>
          <v-time-picker
            ref="timePicker"
            no-title
            v-model="olderThenTime"
            format="24hr"
            :locale="$i18n.locale"
            @change="
              $refs.timeMenu.save(time);
              numberOfAttempsToCleanup();
            "
          ></v-time-picker>
        </v-menu>
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <span v-if="started">
          <v-progress-linear color="primary" indeterminate></v-progress-linear>
        </span>
        <span v-else>{{ $tc("cleanup.text", toDeleteCount) }}</span>
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="auto">
        <v-btn
          @click="cleanupAttempts()"
          v-text="$t('cleanup.button')"
          :disabled="started || toDeleteCount === 0"
        ></v-btn>
      </v-col>
      <v-col class="text--primary align-self-center">
        <span class="success--text bold">{{ lastSuccess }}</span>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { mapActions, mapState } from "vuex";
import axios from "axios";

export default {
  name: "SushiAttemptCleanupWidget",

  components: {},

  props: {},

  data() {
    return {
      time: null,
      started: false,
      toDeleteCount: 0,
      olderThenDate: new Date().toISOString().substr(0, 10),
      olderThenDateMenu: null,
      olderThenTime: new Date().toTimeString().substr(0, 5),
      olderThenTimeMenu: null,
      lastSuccess: "",
    };
  },

  computed: {
    ...mapState({
      organizationId: "selectedOrganizationId",
    }),
    olderThan() {
      let calculated_date = new Date(
        `${this.olderThenDate}T${this.olderThenTime}:00`
      );
      return calculated_date.toISOString();
    },
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    async numberOfAttempsToCleanup() {
      this.started = true;
      let params = { older_than: this.olderThan };
      if (this.organizationId && this.organizationId >= 0) {
        params["organization"] = this.organizationId;
      }
      try {
        let response = await axios.get(
          `/api/sushi-fetch-attempt/cleanup/`,
          { params: params },
          {}
        );
        this.toDeleteCount = response.data.count;
      } catch (error) {
        this.showSnackbar({
          content: "Error starting attempt cleanup: " + error,
          color: "error",
        });
      } finally {
        this.started = false;
      }
    },
    async cleanupAttempts() {
      this.started = true;
      this.lastSuccess = "";
      let data = { older_than: this.olderThan };
      if (this.organizationId && this.organizationId >= 0) {
        data.organization = this.organizationId;
      }
      try {
        let response = await axios.post(
          `/api/sushi-fetch-attempt/cleanup/`,
          data,
          {}
        );
        this.lastSuccess = this.$tc("cleanup.done", response.data.count);
      } catch (error) {
        this.showSnackbar({
          content: "Error starting attempt cleanup: " + error,
          color: "error",
        });
      } finally {
        this.started = false;
      }
      await this.numberOfAttempsToCleanup();
    },
    async startup() {
      this.lastSuccess = "";
      await this.numberOfAttempsToCleanup();
    },
  },

  mounted() {
    this.startup();
  },
};
</script>

<style scoped></style>
