<i18n lang="yaml">
en:
  is_superuser: Superuser
  is_from_master_organization: Consortium staff
  associated_organizations: Associated organizations
  associated_organizations_note:
    Super users and consortium staff users have access to all available organizations, but only
    those listed below are explicitly associated with this account
  organization: Organization
  is_admin: Admin
  unverified_email:
    Your email address has not been verified. Some functions of Celus will not be available.
    Check your email for a verification message from Celus.
  resend_verification_email: Resend verification email
  verification_resent: Verification email was resent
  logout: Log out
  change_password: Change password
  impersonification:
    title: Impersonification
    email: Email
    text: You are a consortial manager, so you can switch to other user accounts.
    first_name: First name
    last_name: Last name
    real_user: you
    search: Search
    stop: Stop impersonification
    organizations: Organizations
    member: Member of organization
    admin: Admin of organization
    manager: Manager of entire consortium

cs:
  is_superuser: Superuživatel
  is_from_master_organization: Člen konzorciálního týmu
  associated_organizations: Přiřazené organizace
  associated_organizations_note:
    Superuživatelé a členové konzorciálního týmu mají přístup ke všem organizacím. Níže jsou
    uvedené jen ty, ke kterým je uživatel explicitně přiřazen.
  organization: Organizace
  is_admin: Administrátor
  unverified_email:
    Vaše emailová adresa nebyla ověřená. Některé funkce systému nebudou k dispozici.
    Zkontrolujte ověřovací email od aplikace Celus ve své schránce.
  resend_verification_email: Znovu zaslat ověřovací email
  verification_resent: Ověřovací email byl znovu zaslán
  logout: Odhlásit se
  change_password: Změnit heslo
  impersonification:
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
</i18n>

<template>
  <v-container v-if="loggedIn && user" class="text-center">
    <v-row>
      <v-col>
        <v-alert
          v-if="!emailVerified"
          type="warning"
          class="ma-3 pa-5"
          outlined
        >
          {{ $t("unverified_email") }}
          <div>
            <v-btn
              color="primary"
              @click="resendVerificationEmail()"
              class="my-5"
            >
              {{ $t("resend_verification_email") }}
            </v-btn>
          </div>
        </v-alert>
      </v-col>
    </v-row>

    <v-row no-gutters>
      <v-col>
        <v-avatar color="primary" class="mt-10" size="80">
          <v-gravatar :email="user.email" :alt="avatarText" default-img="mp">
          </v-gravatar>
        </v-avatar>
      </v-col>
    </v-row>

    <v-row no-gutters>
      <v-col>
        <h3 v-if="user.first_name || user.last_name" class="subdued mt-3">
          {{ user.first_name ? user.first_name : "" }}
          {{ user.last_name ? user.last_name : "" }}
        </h3>
        <h4 v-if="user.email" class="font-weight-light mb-1">
          {{ user.email }}
        </h4>
        <div class="font-weight-black">
          <span v-if="user.is_superuser" v-text="$t('is_superuser')"></span>
          <span
            v-else-if="user.is_from_master_organization"
            v-text="$t('is_from_master_organization')"
          ></span>
        </div>
      </v-col>
    </v-row>

    <v-row class="mb-8" justify="center">
      <v-card elevation="0">
        <v-card-actions>
          <v-btn
            color="purple"
            v-if="impersonated"
            v-text="$t('impersonification.stop')"
            @click="stopImpersonate"
            dark
          ></v-btn>
          <v-btn v-if="canLogout" @click="logout" v-text="$t('logout')"></v-btn>
          <v-btn
            v-if="usesPasswordLogin"
            @click="showPasswordChangeDialog = true"
            v-text="$t('change_password')"
          ></v-btn>
          <PasswordChangeDialog v-model="showPasswordChangeDialog" />
        </v-card-actions>
      </v-card>
    </v-row>

    <v-row>
      <v-col>
        <h2 v-text="$t('associated_organizations')"></h2>
        <div
          class="font-weight-light mt-2 mb-4"
          v-if="user.is_superuser || user.is_from_master_organization"
          v-text="'* ' + $t('associated_organizations_note')"
        ></div>
      </v-col>
    </v-row>

    <v-row>
      <v-col>
        <v-data-table :items="organizationList" :headers="headers">
          <template v-slot:item.is_admin="{ item }">
            <CheckMark :value="item.is_admin" />
          </template>
        </v-data-table>
      </v-col>
    </v-row>

    <v-row v-if="showImpersonate" class="mb-2" align="center" justify="center">
      <v-col cols="12" md="10">
        <h2 v-text="$t('impersonification.title')"></h2>
        <div class="font-weight-light mt-2 mb-4">
          {{ $t("impersonification.text") }}
        </div>
        <v-data-table
          :headers="impersonateHeaders"
          :items="impersonateData"
          item-key="pk"
          :loading="!impersonateLoaded"
          :search="impersonateSearch"
          :item-class="(item) => (item.current ? 'bold' : '')"
          fixed-header
          sort-by="email"
          :footer-props="{ itemsPerPageOptions: [10, 25, 50] }"
          :custom-filter="searchImpersonateFilter"
        >
          <template v-slot:top>
            <v-container>
              <v-row>
                <v-col cols="0" md="1">
                  <v-spacer />
                </v-col>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model="impersonateSearch"
                    :label="$t('impersonification.search')"
                    class=""
                  ></v-text-field>
                </v-col>
              </v-row>
            </v-container>
          </template>
          <template v-slot:item.current="{ item }">
            <v-btn
              icon
              outlined
              :disabled="item.current"
              :color="item.current ? '' : 'purple'"
              @click="() => impersonateUser(item.pk)"
            >
              <v-icon small :class="item.real_user ? 'text-primary' : ''">
                fa fa-arrow-right
              </v-icon>
            </v-btn>
          </template>
          <template v-slot:item.email="{ item }">
            <v-tooltip
              bottom
              v-if="item.is_superuser || item.is_from_master_organization"
            >
              <template #activator="{ on }">
                <v-icon v-on="on" small color="amber" class="mr-1">
                  fas fa-crown
                </v-icon>
              </template>
              {{ $t("impersonification.manager") }}
            </v-tooltip>
            <v-badge
              v-if="item.real_user"
              color="error"
              :content="$t('impersonification.real_user')"
            >
              <span>{{ item.email }}</span>
            </v-badge>
            <span v-else>{{ item.email }}</span>
          </template>
          <template v-slot:item.organizations="{ item }">
            <span
              :key="organization.pk"
              v-for="organization in processOrganizations(item.organizations)"
            >
              <v-tooltip bottom>
                <template #activator="{ on }">
                  <v-chip outlined label v-on="on">
                    <v-icon
                      v-if="organization.is_admin"
                      color="yellow"
                      class="mr-2"
                      x-small
                    >
                      fas fa-star
                    </v-icon>
                    {{ organization.short_name }}
                  </v-chip>
                </template>
                <span
                  v-if="organization.is_admin"
                  v-html="$t('impersonification.admin')"
                />
                <span v-else v-html="$t('impersonification.member')" />
                <strong class="ml-1">{{ organization.name }}</strong>
              </v-tooltip>
            </span>
          </template>
        </v-data-table>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { mapActions, mapGetters, mapState } from "vuex";
import VGravatar from "vue-gravatar";
import CheckMark from "@/components/util/CheckMark";
import axios from "axios";
import PasswordChangeDialog from "@/components/account/PasswordChangeDialog";

export default {
  name: "UserPage",
  components: { PasswordChangeDialog, VGravatar, CheckMark },
  data() {
    return {
      showPasswordChangeDialog: false,
      impersonateData: [],
      impersonateLoaded: false,
      impersonateRequested: false,
      impersonateSearch: "",
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
    }),
    headers() {
      return [
        {
          text: this.$t("organization"),
          value: "name",
        },
        {
          text: this.$t("is_admin"),
          value: "is_admin",
        },
      ];
    },
    organizationList() {
      return Object.values(this.organizations).filter((item) => item.is_member);
    },
    showImpersonate() {
      return (
        this.user.is_from_master_organization ||
        this.user.is_superuser ||
        this.impersonated
      );
    },
    impersonateHeaders() {
      return [
        {
          text: "",
          value: "current",
          sortable: false,
          align: "right",
        },
        {
          text: this.$t("impersonification.email"),
          value: "email",
          sortable: true,
        },
        {
          text: this.$t("impersonification.first_name"),
          value: "first_name",
          sortable: true,
        },
        {
          text: this.$t("impersonification.last_name"),
          value: "last_name",
          sortable: true,
        },
        {
          text: this.$t("impersonification.organizations"),
          value: "organizations",
          sortable: false,
        },
      ];
    },
    impersonated() {
      return !!this.impersonator;
    },
  },

  methods: {
    ...mapActions({
      logout: "logout",
      loadUserData: "loadUserData",
      showSnackbar: "showSnackbar",
    }),
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
        return value.some((rec) =>
          match(rec.organization.short_name, search)
          || match(rec.organization.name, search)
        );
      }

      return false;
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

<style scoped></style>
