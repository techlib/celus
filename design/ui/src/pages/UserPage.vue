<i18n lang="yaml">
en:
  is_superuser: Superuser
  is_admin_of_master_organization: Consortium staff
  is_user_of_master_organization: Consortium observer
  associated_organizations: Associated organizations
  associated_organizations_note:
    Super users and consortium users have access to all available organizations, but only
    those listed below are explicitly associated with this account
  organization: Organization
  is_admin: Admin
  unverified_email:
    Your email address has not been verified. Some functions of CELUS will not be available.
    Check your email for a verification message from CELUS.
  resend_verification_email: Resend verification email
  verification_resent: Verification email was resent
  logout: Log out
  change_password: Change password
  impersonation:
    title: Impersonation
    email: Email
    text: You are a consortial manager, so you can switch to other user accounts.
    first_name: First name
    last_name: Last name
    real_user: you
    search: Search
    stop: Stop impersonation
    organizations: Organizations
    member: Member of organization
    admin: Admin of organization
    manager: Manager of entire consortium
    consortial_user: User of entire consortium
  harvest_reports:
    send: Send the latest harvest report
    sent: The latest harvest report was sent.
    title: Send Harvest reports
    tooltip: When enabled, CELUS will send you a monthly overview email of harvesting success in the previous month
    switched_on: Sending of regular harvest reports for organization '{organization}' has been enabled.
    switched_off: Sending of regular harvest reports for organization '{organization}' has been disabled.

cs:
  is_superuser: Superuživatel
  is_admin_of_master_organization: Správce konzorciálního týmu
  is_user_of_master_organization: Uživatel konzorciálního týmu
  associated_organizations: Přiřazené organizace
  associated_organizations_note:
    Superuživatelé a členové konzorciálního týmu mají přístup ke všem organizacím. Níže jsou
    uvedené jen ty, ke kterým je uživatel explicitně přiřazen.
  organization: Organizace
  is_admin: Administrátor
  unverified_email:
    Vaše emailová adresa nebyla ověřená. Některé funkce systému nebudou k dispozici.
    Zkontrolujte ověřovací email od aplikace CELUS ve své schránce.
  resend_verification_email: Znovu zaslat ověřovací email
  verification_resent: Ověřovací email byl znovu zaslán
  logout: Odhlásit se
  change_password: Změnit heslo
  impersonation:
    title: Zosobnění
    text: Jako správce konzorcia se můžete přepnout do účtů dalších uživatelů.
    email: E-mail
    first_name: Jméno
    last_name: Příjmení
    real_user: vy
    search: Vyhledávání
    stop: Zastavit zosobnění
    organizations: Organizace
    member: Člen organizace
    admin: Administrátor organizace
    manager: Správce celého konzorcia
    consortial_user: Uživatel celého konzorcia
  harvest_reports:
    send: Odeslat nejnovější zprávu o stahování
    sent: Nejnovější zpráva o stahování byla odeslána.
    title: Odesílat zprávy o stahování
    tooltip: Pokud je zapnuto, CELUS bude každý posílat email s přehledem o úspěšných stahováních z předchozího měsíce
    switched_on: Odesílání pravidelných zpráv o stahování pro organizaci '{organization}' bylo aktivováno.
    switched_off: Odesílání pravidelných zpráv o stahování pro organizaci '{organization}' bylo vypnuto.
</i18n>

<template>
  <v-container v-if="loggedIn && user" max-width="1000px">
    <v-row class="text-center">
      <v-col>
        <!--
          please note that normal user will not see this, as he will be
          prevented from seeing anything in CELUS until he verifies his email.
          It may still be useful for superadmins impersonating ordinary users,
          so I am keeping it in.
         -->
        <v-alert
          v-if="!emailVerified"
          type="warning"
          class="ma-3 pa-5"
          variant="outlined"
        >
          {{ $t("unverified_email") }}
          <div>
            <v-btn
              color="primary"
              @click="resendVerificationEmail"
              class="my-5"
            >
              {{ $t("resend_verification_email") }}
            </v-btn>
          </div>
        </v-alert>
      </v-col>
    </v-row>
    <v-row no-gutters class="text-center">
      <v-col>
        <v-avatar color="primary" class="mt-10" size="80">
          <img :src="gravatar" :alt="avatarText" />
        </v-avatar>
      </v-col>
    </v-row>
    <v-row no-gutters class="text-center">
      <v-col>
        <h3 v-if="user.first_name || user.last_name" class="subdued mt-3">
          {{ user.first_name ? user.first_name : "" }}
          {{ user.last_name ? user.last_name : "" }}
        </h3>
        <h4 v-if="user.email" class="font-weight-light mb-1">
          {{ user.email }}
          <v-icon
            v-if="allowUserManagement"
            @click="showUserEditDialog = true"
            size="x-small"
            class="mb-1 ml-1"
            color="lighterIcons"
            >fas fa-edit</v-icon
          >
        </h4>
        <div class="font-weight-black">
          <span v-if="user.is_superuser" v-text="$t('is_superuser')"></span>
          <span
            v-else-if="user.is_admin_of_master_organization"
            v-text="$t('is_admin_of_master_organization')"
          ></span>
          <span
            v-else-if="user.is_user_of_master_organization"
            v-text="$t('is_user_of_master_organization')"
          ></span>
        </div>
      </v-col>
    </v-row>
    <v-dialog
      v-model="showUserEditDialog"
      v-if="showUserEditDialog"
      max-width="1000px"
    >
      <AccountCreateModifyWidget
        :account="user"
        @cancel="cancelUserEditDialog"
        @success="successUserEdit"
        :editMode="true"
      >
      </AccountCreateModifyWidget>
    </v-dialog>
    <v-row class="mb-5 text-center" justify="center" no-gutters>
      <v-card elevation="0">
        <v-card-actions>
          <v-btn
            variant="elevated"
            color="purple"
            v-if="impersonated"
            @click="stopImpersonate"
            dark
          >
            {{ $t("impersonation.stop") }}
          </v-btn>
          <v-btn
            v-if="canLogout"
            @click="logout"
            variant="elevated"
            color="defaultButton"
            >{{ $t("logout") }}</v-btn
          >
          <v-btn
            v-if="usesPasswordLogin"
            @click="showPasswordChangeDialog = true"
            variant="elevated"
            color="defaultButton"
            >{{ $t("change_password") }}</v-btn
          >
          <PasswordChangeDialog
            v-model="showPasswordChangeDialog"
          ></PasswordChangeDialog>
        </v-card-actions>
      </v-card>
    </v-row>
    <v-divider thickness="4" color="secondary" opacity="0.4" class="my-12" />
    <v-row class="text-center">
      <v-col>
        <h2>{{ $t("associated_organizations") }}</h2>
        <div
          class="font-weight-light mt-2 mb-4"
          v-if="user.is_superuser || user.is_user_of_master_organization"
          v-text="'* ' + $t('associated_organizations_note')"
        ></div>
      </v-col>
    </v-row>
    <v-row>
      <v-col class="text-left">
        <v-data-table
          :items="organizationList"
          :headers="headers"
          :items-per-page-options="[10, 25, 50, -1]"
          :hide-default-footer="organizationList.length <= 10"
        >
          <template #item.is_admin="{ item }">
            <CheckMark
              :model-value="item.is_admin"
              icon-size="default"
            ></CheckMark>
          </template>
          <template #item.send_harvest_reports="{ item }">
            <v-btn
              variant="text"
              icon
              @click="toggleSendHarvestReports(item)"
              :disabled="!harvestReportsEnabled(item, user)"
            >
              <CheckMark
                true-color="success"
                :true-tooltip="$t('harvest_reports.tooltip')"
                :false-tooltip="$t('harvest_reports.tooltip')"
                :model-value="item.send_harvest_reports"
              ></CheckMark>
            </v-btn>
            <v-tooltip location="bottom">
              <template #activator="{ props }">
                <v-btn
                  variant="text"
                  icon
                  v-bind="props"
                  @click="sendHarvestReport(item)"
                  :disabled="!harvestReportsEnabled(item, user)"
                >
                  <v-icon
                    color="info"
                    size="small"
                    :class="harvestReportsEnabled(item, user) ? '' : 'd-none'"
                  >
                    fas fa-envelope
                  </v-icon>
                </v-btn>
              </template>
              {{ $t("harvest_reports.send") }}
            </v-tooltip>
          </template>
        </v-data-table>
      </v-col>
    </v-row>
    <v-divider
      thickness="4"
      color="secondary"
      opacity="0.4"
      class="my-12"
      v-if="showImpersonate"
    />
    <v-row
      v-if="showImpersonate"
      class="mb-2 text-center"
      align="center"
      justify="center"
    >
      <v-col cols="12" md="10">
        <h2 v-text="$t('impersonation.title')"></h2>
        <div class="font-weight-light mt-2 mb-4">
          {{ $t("impersonation.text") }}
        </div>
        <v-data-table
          :headers="impersonateHeaders"
          :items="impersonateData"
          item-key="pk"
          item-value="pk"
          :loading="!impersonateLoaded"
          :search="impersonateSearch"
          :item-class="(item) => (item.current ? 'bold' : '')"
          density="comfortable"
          fixed-header
          v-model:sort-by="orderBy"
          :items-per-page-options="[10, 25, 50]"
          :custom-filter="searchImpersonateFilter"
        >
          <template #top>
            <v-container>
              <v-row>
                <v-col cols="0" md="1">
                  <v-spacer></v-spacer>
                </v-col>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model="impersonateSearch"
                    :label="$t('impersonation.search')"
                  ></v-text-field>
                </v-col>
              </v-row>
            </v-container>
          </template>
          <template #item.current="{ item }">
            <v-btn
              icon
              size="x-small"
              variant="outlined"
              :disabled="item.current"
              :color="item.current ? '' : 'purple'"
              @click="() => impersonateUser(item.pk)"
            >
              <v-icon
                size="small"
                :class="item.real_user ? 'text-primary' : ''"
              >
                fa fa-arrow-right
              </v-icon>
            </v-btn>
          </template>
          <template #item.email="{ item }">
            <div class="email_cell">
              <v-tooltip
                location="bottom"
                v-if="item.is_superuser || item.is_admin_of_master_organization"
              >
                <template #activator="{ props }">
                  <v-icon
                    v-bind="props"
                    size="small"
                    color="amber"
                    class="mr-1"
                  >
                    fas fa-crown
                  </v-icon>
                </template>
                {{ $t("impersonation.manager") }}
              </v-tooltip>
              <v-tooltip
                location="bottom"
                v-else-if="item.is_user_of_master_organization"
              >
                <template #activator="{ props }">
                  <v-icon
                    v-bind="props"
                    size="small"
                    color="blue-grey lighten-2"
                    class="mr-1"
                  >
                    fas fa-crown
                  </v-icon>
                </template>
                {{ $t("impersonation.consortial_user") }}
              </v-tooltip>
              <v-badge
                v-if="item.real_user"
                color="error"
                :content="$t('impersonation.real_user')"
                floating
                location="top end"
              >
                <span>{{ item.email }}</span>
              </v-badge>
              <span v-else>{{ item.email }}</span>
            </div>
          </template>
          <template #item.first_name="{ item }">
            <div class="email_cell">
              {{ item.first_name }}
            </div>
          </template>
          <template #item.last_name="{ item }">
            <div class="email_cell">
              {{ item.last_name }}
            </div>
          </template>
          <template #item.organizations="{ item }">
            <div class="email_cell">
              <span
                :key="organization.pk"
                v-for="organization in processOrganizations(item.organizations)"
              >
                <v-tooltip location="bottom">
                  <template #activator="{ props }">
                    <v-chip variant="outlined" label v-bind="props">
                      <v-icon
                        v-if="organization.is_admin"
                        color="yellow"
                        class="mr-2"
                        size="x-small"
                      >
                        fas fa-star
                      </v-icon>
                      {{ organization.short_name }}
                    </v-chip>
                  </template>
                  <span
                    v-if="organization.is_admin"
                    v-html="$t('impersonation.admin')"
                  ></span>
                  <span v-else v-html="$t('impersonation.member')"></span>
                  <strong class="ml-1">{{ organization.name }}</strong>
                </v-tooltip>
              </span>
            </div>
          </template>
        </v-data-table>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { mapActions, mapGetters, mapState } from "vuex";
import CheckMark from "@/components/util/CheckMark";
import axios from "axios";
import PasswordChangeDialog from "@/components/account/PasswordChangeDialog";
import AccountCreateModifyWidget from "@/components/account/AccountCreateModifyWidget.vue";
import md5 from "md5";
import VGravatar from "vue3-gravatar";

export default {
  name: "UserPage",
  components: {
    PasswordChangeDialog,
    VGravatar,
    CheckMark,
    AccountCreateModifyWidget,
  },
  data() {
    return {
      orderBy: [{ key: "email", order: "asc" }],
      showPasswordChangeDialog: false,
      impersonateData: [],
      impersonateLoaded: false,
      impersonateRequested: false,
      showUserEditDialog: false,
      impersonateSearch: "",
      defaultImg: "mp",
    };
  },
  computed: {
    ...mapState({
      organizations: "organizations",
      user: "user",
    }),
    ...mapGetters({
      loggedIn: "loggedIn",
      avatarText: "avatarText",
      usernameText: "usernameText",
      canLogout: "canLogout",
      impersonator: "impersonator",
      emailVerified: "emailVerified",
      usesPasswordLogin: "usesPasswordLogin",
      allowUserManagement: "allowUserManagement",
    }),
    headers() {
      return [
        {
          title: this.$t("organization"),
          value: "name",
          key: "name",
          align: "start",
        },
        {
          title: this.$t("is_admin"),
          value: "is_admin",
          key: "is_admin",
          align: "center",
          sortable: false,
        },
        {
          title: this.$t("harvest_reports.title"),
          value: "send_harvest_reports",
          key: "send_harvest_reports",
          align: "center",
          sortable: false,
        },
      ];
    },
    organizationList() {
      if (!this.organizations) {
        return [];
      }
      return Object.values(this.organizations).filter((item) => item.is_member);
    },
    showImpersonate() {
      return (
        this.user.is_admin_of_master_organization ||
        this.user.is_superuser ||
        this.impersonated
      );
    },
    impersonateHeaders() {
      return [
        {
          title: "",
          value: "current",
          sortable: false,
          align: "end",
        },
        {
          title: this.$t("impersonation.email"),
          value: "email",
          key: "email",
          sortable: true,
          align: "start",
        },
        {
          title: this.$t("impersonation.first_name"),
          value: "first_name",
          key: "first_name",
          sortable: true,
        },
        {
          title: this.$t("impersonation.last_name"),
          value: "last_name",
          key: "last_name",
          sortable: true,
        },
        {
          title: this.$t("impersonation.organizations"),
          value: "organizations",
          sortable: false,
        },
      ];
    },
    impersonated() {
      return !!this.impersonator;
    },
    gravatar() {
      const hash = md5(this.user.email.trim().toLowerCase());
      return `https://www.gravatar.com/avatar/${hash}?d=mp&s=80`;
    },
  },

  methods: {
    ...mapActions({
      logout: "logout",
      loadUserData: "loadUserData",
      showSnackbar: "showSnackbar",
    }),
    cancelUserEditDialog() {
      this.showUserEditDialog = false;
    },

    successUserEdit() {
      this.cancelUserEditDialog();
      this.loadUserData();
    },
    async resendVerificationEmail() {
      try {
        await axios.post("/api/user/verify-email");
        this.showSnackbar({
          content: this.$t("verification_resent"),
          color: "success",
        });
      } catch (error) {
        this.showSnackbar({
          content: "Error sending verification email: " + error,
          color: "error",
        });
      }
    },
    async loadImpersonate() {
      try {
        const response = await axios.get("/api/impersonate/");
        this.impersonateData = response.data;
        this.impersonateLoaded = true;
      } catch (error) {
        this.showSnackbar({
          content: "Error fetching impersonate data: " + error,
          color: "error",
        });
      }
    },
    async stopImpersonate() {
      if (this.impersonator) {
        await this.impersonateUser(this.impersonator);
      }
    },

    async impersonateUser(pk) {
      try {
        this.impersonateRequested = true;
        await axios.put(`/api/impersonate/${pk}/`);
        window.location.reload();
      } catch (error) {
        this.showSnackbar({
          content: "Error fetching impersonate data: " + error,
          color: "error",
        });
      } finally {
        this.impersonateRequested = false;
      }
    },
    processOrganizations(organizations) {
      return organizations.map((e) => ({
        pk: e.organization.pk,
        is_admin: e.is_admin,
        name: e.organization.name,
        short_name: e.organization.short_name,
      }));
    },
    searchImpersonateFilter(value, search) {
      // Match value directly
      let match = (value, search) =>
        value && value.toString().toLowerCase().includes(search.toLowerCase());
      if (match(value, search)) {
        return true;
      }
      // Match organization
      if (Array.isArray(value)) {
        return value.some(
          (rec) =>
            match(rec.organization.short_name, search) ||
            match(rec.organization.name, search),
        );
      }

      return false;
    },
    async toggleSendHarvestReports(organization) {
      let enabled = !organization.send_harvest_reports;
      try {
        let response = await axios.post(
          `/api/organization/${organization.pk}/harvest-reports/`,
          { enabled: enabled },
        );
        organization.send_harvest_reports = enabled;
        if (enabled) {
          this.showSnackbar({
            content: this.$t("harvest_reports.switched_on", {
              organization: organization.name,
            }),
            color: "success",
          });
        } else {
          this.showSnackbar({
            content: this.$t("harvest_reports.switched_off", {
              organization: organization.name,
            }),
            color: "success",
          });
        }
      } catch (error) {
        this.showSnackbar({
          content: "Error enabling/disabling harvest reports: " + error,
          color: "error",
        });
      }
    },
    async sendHarvestReport(organization) {
      try {
        let response = await axios.post(
          `/api/organization/${organization.pk}/send-harvest-report/`,
        );
        this.showSnackbar({
          content: this.$t("harvest_reports.sent"),
          color: "success",
        });
      } catch (error) {
        this.showSnackbar({
          content: "Error sending harvest report: " + error,
          color: "error",
        });
      }
    },
    harvestReportsEnabled(organization, user) {
      return (
        organization.is_admin ||
        user.is_superuser ||
        user.is_admin_of_master_organization
      );
    },
  },

  async mounted() {
    // redownload user data on page load to make it is up-to-date
    await this.loadUserData();
    if (this.showImpersonate) {
      this.loadImpersonate();
    }
  },
};
</script>

<style lang="scss" scoped>
.email_cell {
  display: flex;
  justify-content: flex-start;
  align-items: center;
}
.hidden {
  display: "hidden";
}
</style>
