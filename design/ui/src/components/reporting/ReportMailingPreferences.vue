<i18n lang="yaml" src="@/locales/reporting.yaml"></i18n>
<i18n lang="yaml" src="@/locales/dialog.yaml"></i18n>
<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<i18n lang="yaml">
en:
  active: "Active"
  inactive: "Periodic mailing not active"
  default_settings: "Default settings for new activations"
  error_fetching_mailing_objects: "Error fetching mailing objects"
  error_fetching_visible_users: "Error fetching visible users"
  mailing_preferences_intro: |
    Here you can manage the mailing preferences for the report. You can activate or deactivate periodic mailing
    and/or send report export by email immediately.
  you: "You"
  toggle_active_tt: "Toggle to activate or deactivate regular mailing of report export by email"
  fiscal_period_tt: "Use fiscal year as basis for reporting"
  fiscal_month_tt: "User fiscal year start month"
  fiscal_month_irrelevant_tt: "User fiscal year start month - irrelevant when monthly reporting is selected"
cs:
  active: "Aktivní"
  inactive: "Periodické odesílání neaktivní"
  default_settings: "Výchozí nastavení pro nové aktivace"
  error_fetching_mailing_objects: "Chyba při načítání mailovacích objektů"
  error_fetching_visible_users: "Chyba při načítání viditelných uživatelů"
  mailing_preferences_intro: |
    Zde můžete spravovat nastavení odesílání reportů. Můžete aktivovat nebo deaktivovat periodické odesílání
    reportů a/nebo jednorázově odeslat export reportu.
  you: "Vy"
  toggle_active_tt: "Přepnutím se aktivuje nebo deaktivuje periodické odesílání reportu"
  fiscal_period_tt: "Použít fiskální rok jako základ pro odesílání"
  fiscal_month_tt: "Uživatelský měsíc začátku fiskálního roku"
  fiscal_month_irrelevant_tt: "Uživatelský měsíc začátku fiskálního roku - nepoužitelný, pokud je vybráno měsíční odesílání"
</i18n>

<template>
  <v-card class="pa-3">
    <v-card-title>
      {{ $t("mailing_preferences_tt") }}:
      <span class="font-weight-light">{{ report.name }}</span>
    </v-card-title>
    <v-card-text class="ma-1">
      <v-row>
        <v-col>
          <v-alert>
            {{ $t("mailing_preferences_intro") }}
          </v-alert>
        </v-col>
        <v-col cols="auto" :class="{ hide: inactiveCount === 0 }">
          <v-card class="py-2 px-4">
            <span class="text-caption">{{ $t("default_settings") }}:</span>
            <div class="d-flex align-center ga-2">
              <MailingFrequencyWidget
                v-model:frequency="selectedFrequency"
                v-model:numberOfPeriods="numberOfPeriods"
                :trend-mode="trendMode"
              />
              <span v-if="showFiscalPeriod">
                <v-checkbox
                  v-model="fiscalPeriod"
                  :label="$t('fiscal_period')"
                  density="compact"
                  hide-details
                  class="mt-1 ml-4"
                />
              </span>
            </div>
          </v-card>
        </v-col>
      </v-row>

      <v-data-table
        v-model="selectedUsers"
        :headers="headers"
        :items="visibleUsers"
        :loading="loading"
        item-key="pk"
        item-value="pk"
        :items-per-page="10"
        class="pt-4"
        :search="search"
        :hide-default-footer="visibleUsers.length <= 10"
      >
        <template #top>
          <v-row class="align-center pb-2">
            <v-spacer></v-spacer>

            <v-col cols="auto">
              <v-text-field
                v-if="visibleUsers.length > 10"
                v-model="search"
                :label="$t('labels.search')"
                density="compact"
                append-inner-icon="fa-solid fa-magnifying-glass"
                min-width="300"
                hide-details
                clearable
              ></v-text-field>
            </v-col>
          </v-row>
        </template>

        <template #item.active="{ item }">
          <v-tooltip :text="$t('toggle_active_tt')" location="bottom">
            <template #activator="{ props }">
              <v-switch
                @update:model-value="toggleActive(item)"
                :model-value="item.active"
                density="compact"
                hide-details
                color="primary"
                v-bind="props"
              />
            </template>
          </v-tooltip>
        </template>

        <template #item.email="{ item }">
          <v-tooltip :text="$t('you')" location="bottom">
            <template #activator="{ props }">
              <v-icon
                v-if="item.pk === user.pk"
                size="small"
                color="yellow"
                v-bind="props"
                class="mr-2"
                >fa fa-star</v-icon
              >
            </template>
          </v-tooltip>
          {{ item.email }}
        </template>

        <template #item.mailing="{ item }">
          <MailingFrequencyWidget
            v-if="item.mailing"
            v-model:frequency="item.mailing.frequency"
            v-model:numberOfPeriods="item.mailing.number_of_periods"
            @update:mailing="updateMailing(item)"
            :trend-mode="trendMode"
          />
          <span v-else class="text-caption text-disabled">
            {{ $t("inactive") }}
          </span>
        </template>

        <template #item.mailing.fiscal_period="{ item }">
          <div class="d-flex align-center">
            <v-tooltip
              :text="$t('fiscal_period_tt')"
              location="bottom"
              v-if="item.mailing"
            >
              <template #activator="{ props }">
                <v-checkbox
                  v-model="item.mailing.fiscal_period"
                  v-bind="props"
                  density="compact"
                  hide-details
                  @change="updateMailing(item)"
                  :disabled="item.mailing.frequency === 'M'"
                ></v-checkbox>
              </template>
            </v-tooltip>
            <v-tooltip
              :text="
                item.mailing.frequency === 'M'
                  ? $t('fiscal_month_irrelevant_tt')
                  : $t('fiscal_month_tt')
              "
              location="bottom"
              v-if="item.fiscal_year_start_month"
            >
              <template #activator="{ props }">
                <span v-bind="props" class="text-caption text-disabled">
                  {{
                    getMonthAbbreviation(
                      item.fiscal_year_start_month || 0,
                      lang,
                    )
                  }}
                </span>
              </template>
            </v-tooltip>
          </div>
        </template>

        <template #item.mailing.next_send="{ item }">
          <v-tooltip
            :text="$t('next_send_tt')"
            location="bottom"
            v-if="item.mailing"
          >
            <template #activator="{ props }">
              <span v-bind="props" class="text-caption">{{
                item.mailing.next_send
              }}</span>
            </template>
          </v-tooltip>
        </template>

        <template #item.actions="{ item }">
          <v-tooltip :text="$t('send_one_time_email_tt')" location="bottom">
            <template #activator="{ props }">
              <v-btn
                @click="sendOneTimeEmail(item)"
                variant="text"
                size="small"
                color="info"
                icon="fa-solid fa-envelope"
                v-bind="props"
              ></v-btn>
            </template>
          </v-tooltip>
        </template>
      </v-data-table>
    </v-card-text>
    <v-card-actions class="pa-4">
      <v-btn @click="close" variant="elevated">{{ $t("close") }}</v-btn>
    </v-card-actions>
  </v-card>
</template>

<script>
import { mapActions, mapState } from "vuex";
import cancellation from "@/mixins/cancellation";
import MailingFrequencyWidget from "./MailingFrequencyWidget.vue";
import { getMonthAbbreviation } from "@/libs/dates";

export default {
  name: "ReportMailingPreferences",

  components: {
    MailingFrequencyWidget,
  },

  mixins: [cancellation],

  props: {
    report: {
      type: Object,
      required: true,
    },
  },

  emits: ["close"],

  data() {
    return {
      mailingObjects: [],
      visibleUsers: [],
      selectedUsers: [],
      loadingUsers: false,
      loadingMailingObjects: false,
      search: "",

      selectedFrequency: "M",
      numberOfPeriods: 12,
      fiscalPeriod: false,
    };
  },

  computed: {
    ...mapState({
      user: "user",
      lang: "appLanguage",
    }),
    loading() {
      return this.loadingUsers || this.loadingMailingObjects;
    },
    headers() {
      let headers = [
        { title: this.$t("active"), value: "active" },
        { title: this.$t("labels.first_name"), value: "first_name" },
        { title: this.$t("labels.last_name"), value: "last_name" },
        { title: this.$t("labels.email"), value: "email" },
        { title: this.$t("frequency_and_periods_label"), value: "mailing" },
        {
          title: this.$t("next_send"),
          value: "mailing.next_send",
        },
        { title: this.$t("title_fields.actions"), value: "actions" },
      ];
      if (this.showFiscalPeriod) {
        // put fiscal period header after the frequency and periods header
        headers.splice(5, 0, {
          title: this.$t("fiscal_period"),
          value: "mailing.fiscal_period",
        });
      }
      return headers;
    },
    inactiveCount() {
      return this.visibleUsers.filter((user) => !user.active).length;
    },
    showFiscalPeriod() {
      // do not confuse users with fiscal period info if no relevant user has a
      // fiscal period set up
      return this.visibleUsers.some((user) => user.fiscal_year_start_month);
    },
    trendMode() {
      return this.report?.trendMode ?? false;
    },
  },

  methods: {
    ...mapActions(["showSnackbar"]),
    getMonthAbbreviation,
    async fetchMailingObjects() {
      this.loadingMailingObjects = true;
      const result = await this.http({
        url: `/api/flexible-report/${this.report.pk}/mailings/`,
      });
      if (result.error) {
        this.showSnackbar({
          content: this.$t("error_fetching_mailing_objects"),
          color: "error",
        });
      } else {
        this.mailingObjects = result.response.data;
      }
      this.loadingMailingObjects = false;
    },
    async fetchVisibleUsers() {
      this.loadingUsers = true;
      let users = [];
      const result = await this.http({
        url: `/api/flexible-report/${this.report.pk}/view-users/`,
      });
      if (result.error) {
        this.showSnackbar({
          content: this.$t("error_fetching_visible_users"),
          color: "error",
        });
        this.loadingUsers = false;
        return;
      }
      users = result.response.data;
      // post-process the visible users to add info from mailing objects
      users.forEach((user) => {
        user.mailing = this.mailingObjects.find((m) => m.user.pk === user.pk);
        if (user.mailing) {
          this.selectedUsers.push(user.pk);
          user.active = true;
        } else {
          user.active = false;
        }
      });
      // order visible users to that current user is first, selected users after that
      users.sort((a, b) => {
        if (a.pk === this.user.pk) return -1;
        if (b.pk === this.user.pk) return 1;
        return (
          this.selectedUsers.indexOf(b.pk) - this.selectedUsers.indexOf(a.pk)
        );
      });
      this.visibleUsers = users;
      this.loadingUsers = false;
    },
    async sendOneTimeEmail(user) {
      const response = await this.http({
        url: "/api/report-mailing/test/",
        method: "POST",
        data: {
          flexible_report: this.report.pk,
          user: user.pk,
          frequency: user.mailing
            ? user.mailing.frequency
            : this.selectedFrequency,
          number_of_periods: user.mailing
            ? user.mailing.number_of_periods
            : this.numberOfPeriods,
        },
        showError: true,
      });
      if (response.error) {
        let error = "";
        if (response.error.response?.data?.non_field_errors) {
          error = response.error.response.data.non_field_errors[0];
        } else if (response.error.response?.data?.number_of_periods) {
          error = response.error.response.data.number_of_periods[0];
        }
        if (error) {
          error = ": " + error;
        }
        this.showSnackbar({
          content: this.$t("error_sending_one_time_email") + error,
          color: "error",
        });
      } else {
        this.showSnackbar({
          content: this.$t("one_time_email_sent"),
          color: "success",
        });
      }
    },
    async toggleActive(user) {
      if (user.active) {
        await this.deactivate(user);
      } else {
        await this.activate(user);
      }
    },
    async activate(user) {
      if (!user.mailing) {
        // create a new record
        const response = await this.http({
          url: "/api/report-mailing/",
          method: "POST",
          data: {
            flexible_report: this.report.pk,
            user: user.pk,
            frequency: this.selectedFrequency,
            number_of_periods: this.numberOfPeriods,
            fiscal_period: this.fiscalPeriod,
          },
        });
        if (response.error) {
          this.showSnackbar({
            content: this.$t("error_activating_mailing"),
            color: "error",
          });
        } else {
          user.mailing = response.response.data;
          user.active = true;
          this.showSnackbar({
            content: this.$t("mailing_activated"),
            color: "success",
          });
        }
      }
    },
    async deactivate(user) {
      const response = await this.http({
        url: `/api/report-mailing/${user.mailing.pk}/`,
        method: "DELETE",
      });
      if (response.error) {
        this.showSnackbar({
          content: this.$t("error_deactivating_mailing"),
          color: "error",
        });
      } else {
        user.mailing = null;
        user.active = false;
        this.showSnackbar({
          content: this.$t("mailing_deactivated"),
          color: "success",
        });
      }
    },
    async updateMailing(user) {
      const response = await this.http({
        url: `/api/report-mailing/${user.mailing.pk}/`,
        method: "PATCH",
        data: {
          frequency: user.mailing.frequency,
          number_of_periods: user.mailing.number_of_periods,
          fiscal_period: user.mailing.fiscal_period,
        },
      });
      if (response.error) {
        this.showSnackbar({
          content: this.$t("error_updating_mailing"),
          color: "error",
        });
      } else {
        user.mailing.frequency = response.response.data.frequency;
        user.mailing.number_of_periods =
          response.response.data.number_of_periods;
        user.mailing.fiscal_period = response.response.data.fiscal_period;
        user.mailing.next_send = response.response.data.next_send;
        this.showSnackbar({
          content: this.$t("mailing_updated"),
          color: "success",
        });
      }
    },
    close() {
      this.$emit("close");
    },
  },

  async mounted() {
    await this.fetchMailingObjects();
    await this.fetchVisibleUsers();
  },
};
</script>

<style scoped>
.hide {
  visibility: hidden;
}
</style>
