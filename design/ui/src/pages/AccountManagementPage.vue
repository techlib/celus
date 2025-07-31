<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<i18n lang="yaml">
en:
  already_verified: This user is already verified.
  cannot_delete: You cannot remove the user that is currently logged in.
  create_new_user: Create a new user
  delete_prompt: Are you sure you want to remove user {first_name} {last_name} ({username}) from this organization?
  delete_user: Delete user
  edit_user: Modify user
  error_delete: Error while removing user
  error_send_invitation: Error sending invitation email
  error_send_verification: Error sending verification email
  is_admin: Admin
  select_organization: Select an organization
  send: Send
  send_invitation: Send invitation email
  send_invitation_to: Send invitation email to
  send_verification: Send verification email
  send_verification_to: Send verification email to
  success_delete: User successfully removed from this organization
  success_send_invitation: Invitation link was successfully sent
  success_send_verification: Verification link was successfully sent
  superactions: Special Actions
cs:
  already_vetified: Tento uživatel již byl ověřen.
  cannot_delete: Nemůžete smazat aktuálně přihlášeného uživatele.
  create_new_user: Vytvořit nového uživatele
  delete_prompt: Opravdu chcete smazat uživatele {first_name} {last_name} ({username}) z této organizace?
  delete_user: Smazat uživatele
  edit_user: Upravit uživatele
  error_delete: Při mazání uživatele došlo k chybě
  error_send_invitation: Při odesílání pozvánky došlo k chybě
  error_send_verification: Při odesílání ověřovacího emailu došlo k chybě
  is_admin: Admin
  select_organization: Zvolte organizaci
  send: Odeslat
  send_invitation: Odeslat pozvánku emailem
  send_invitation_to: Odeslat pozvánku emailem uživateli
  send_verification: Odeslat ověřovací email
  send_verification_to: Odeslat ověřovací email uživateli
  success_delete: Uživatel byl úspěšně smazán z vybrané organizace
  success_send_invitation: Email s pozvánkou byl úspěšne odeslán
  success_send_verification: Email s ověřovacím odkazem byl úspěšně odeslán
  superactions: Speciální akce
</i18n>

<template>
  <div>
    <v-dialog
      v-if="showCreateDialog"
      v-model="showCreateDialog"
      max-width="1000px"
    >
      <AccountCreateModifyWidget
        @cancel="closeDialog"
        @success="successCreate"
        @send_email="sendInvitationEmail"
        :organizationList="orgList"
        :selectedOrganization="selectedOrganization"
        :editMode="false"
      ></AccountCreateModifyWidget>
    </v-dialog>
    <v-dialog v-if="showEditDialog" v-model="showEditDialog" max-width="1000px">
      <AccountCreateModifyWidget
        :account="selectedAccount"
        @cancel="closeEditDialog"
        @success="successEdit"
        :organizationList="orgList"
        :selectedOrganization="selectedOrganization"
        :editMode="true"
      ></AccountCreateModifyWidget>
    </v-dialog>
    <v-dialog v-model="showDeleteDialog" max-width="620px">
      <v-card class="pb-2">
        <v-card-title> {{ $t("actions.delete") }} </v-card-title>
        <v-card-text>
          <p class="text-disabled delete_info">
            {{
              $t("delete_prompt", {
                first_name: selectedAccount.first_name,
                last_name: selectedAccount.last_name,
                username: selectedAccount.username,
              })
            }}
          </p>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn
            @click="closeDeleteDialog()"
            variant="elevated"
            color="defaultButton"
          >
            {{ $t("actions.cancel") }}</v-btn
          >
          <v-btn @click="deleteAccount()" color="error" variant="elevated">
            <v-icon class="mr-2" size="small">fa fa-trash</v-icon>
            {{ $t("actions.delete") }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    <v-dialog v-model="showSendEmailDialog" max-width="620px">
      <v-card class="pb-2">
        <v-card-title>
          {{
            emailType == "invitation"
              ? $t("send_invitation")
              : $t("send_verification")
          }}
        </v-card-title>
        <v-card-text>
          {{
            emailType == "invitation"
              ? $t("send_invitation_to")
              : $t("send_verification_to")
          }}
          {{ selectedAccount.first_name }} {{ selectedAccount.last_name }} ({{
            selectedAccount.username
          }}) ?
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn
            @click="closeSendEmailDialog()"
            color="defaultButton"
            variant="elevated"
          >
            {{ $t("actions.cancel") }}
          </v-btn>
          <v-btn @click="sendUserEmail()" color="primary" variant="elevated">
            <v-icon class="mr-2" size="small">fas fa-envelope</v-icon>
            {{ $t("send") }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    <v-container>
      <v-row>
        <v-col cols="12" sm="6" lg="4">
          <v-autocomplete
            v-if="orgItems.length > 1"
            v-model="selectedOrganization"
            :items="orgList"
            item-value="pk"
            :label="$t('select_organization')"
            class="ml-2 mt-3"
            item-title="name"
            hide-details
          ></v-autocomplete>
        </v-col>
      </v-row>
      <v-row>
        <v-col>
          <v-btn
            :disabled="!(isAdmin || showManagementStuff)"
            @click="showCreateDialog = true"
            class="ml-2 mt-3"
            color="primary"
          >
            <v-icon class="mr-2" size="small">fas fa-user-plus</v-icon>
            {{ $t("create_new_user") }}
          </v-btn>
        </v-col>
        <v-spacer></v-spacer>
        <v-col>
          <v-text-field
            v-model="search"
            prepend-icon="fas fa-search"
            single-line
            hide-details
            :label="$t('labels.search')"
          ></v-text-field>
        </v-col>
      </v-row>
      <v-row class="mt-0 pt-0">
        <v-col>
          <v-data-table
            v-if="orgUsers.length > 0"
            :items="orgUsers"
            density="comfortable"
            :headers="headers"
            :search="search"
          >
            <template #item.is_admin="{ item }">
              <CheckMark :model-value="getIsAdmin(item)"></CheckMark>
            </template>
            <template #item.actions="{ item }">
              <v-tooltip max-width="600px" location="bottom">
                <template #activator="{ props }">
                  <v-icon
                    @click="deleteItem(item)"
                    class="mr-2 text-grey"
                    size="small"
                    v-bind="props"
                    >fas fa-trash
                  </v-icon>
                </template>
                <span>{{ $t("delete_user") }}</span>
              </v-tooltip>
              <v-tooltip max-width="600px" location="bottom">
                <template #activator="{ props }">
                  <v-icon
                    @click="editItem(item)"
                    class="mr-2 text-grey"
                    size="small"
                    v-bind="props"
                    >fas fa-edit
                  </v-icon>
                </template>
                <span>{{ $t("edit_user") }}</span>
              </v-tooltip>
              <v-tooltip max-width="600px" location="bottom">
                <template v-slot:activator="{ props }">
                  <v-icon
                    class="text-grey"
                    @click="sendEmail(item, 'invitation')"
                    size="small"
                    v-bind="props"
                    >fas fa-envelope</v-icon
                  >
                </template>
                <span> {{ $t("send_invitation") }}</span>
              </v-tooltip>
            </template>
            <template v-if="showSuperActions" #item.superactions="{ item }">
              <v-tooltip max-width="600px" location="bottom">
                <template v-slot:activator="{ props }">
                  <v-icon
                    @click="sendEmail(item, 'verification')"
                    size="small"
                    class="text-grey"
                    v-bind="props"
                    >fas fa-envelope-open</v-icon
                  >
                </template>
                <span> {{ $t("send_verification") }}</span>
              </v-tooltip>
            </template>
          </v-data-table>
        </v-col>
      </v-row>
    </v-container>
  </div>
</template>

<script>
import cancellation from "@/mixins/cancellation";
import { mapState, mapActions, mapGetters } from "vuex";
import AccountCreateModifyWidget from "@/components/account/AccountCreateModifyWidget";
import CheckMark from "@/components/util/CheckMark";

export default {
  name: "AccountManagementPage",
  mixins: [cancellation],
  components: {
    AccountCreateModifyWidget,
    CheckMark,
  },
  data() {
    return {
      usersData: [], //data about all accessible users

      selectedOrganization: null, //pk of selected organization
      selectedAccount: {},
      showCreateDialog: false,
      showEditDialog: false,
      showDeleteDialog: false,
      showSendEmailDialog: false,
      search: "",
      emailType: "invitation", //invitation or verification
    };
  },
  computed: {
    ...mapState({
      user: "user",
    }),

    ...mapGetters({
      orgItems: "organizationItems", //accessible organizations
      orgSelected: "selectedOrganization", //globally selected org
      showManagementStuff: "showManagementStuff",
      allowEmailLogin: "allowEmailLogin",
    }),

    orgList() {
      return Object.values(this.orgItems).filter((item) => item.name != "All");
    },

    isAdmin() {
      //is admin of currently selected org
      const orgMatch = this.orgItems.find(
        (org) => org.pk == this.selectedOrganization,
      );
      return orgMatch.is_admin;
    },

    showSuperActions() {
      // super actions now contain only verification email sending,
      // so we do not want to show them if email login is not allowed
      return this.showManagementStuff && this.allowEmailLogin;
    },

    headers() {
      const baseHeaders = [
        {
          title: this.$t("labels.first_name"),
          value: "first_name",
          sortable: true,
        },
        {
          title: this.$t("labels.last_name"),
          value: "last_name",
          sortable: true,
        },
        { title: this.$t("labels.email"), value: "email", sortable: true },
        {
          title: this.$t("is_admin"),
          value: "is_admin",
          align: "center",
          sortable: true,
        },
        {
          title: this.$t("title_fields.actions"),
          value: "actions",
          sortable: false,
        },
      ];
      if (this.showSuperActions) {
        baseHeaders.push({
          title: this.$t("superactions"),
          value: "superactions",
          sortable: false,
        });
      }
      return baseHeaders;
    },

    orgUsers() {
      //data about users from selected organization
      return this.usersData.filter((item) =>
        item.organizations.some(
          (org) => org.organization.pk === this.selectedOrganization,
        ),
      );
    },
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),

    async fetchUsers() {
      const { response } = await this.http({
        url: "/api/user-management/",
        label: "usersData",
      });
      if (response) {
        this.usersData = response.data;
      }
    },

    getIsAdmin(account) {
      if (this.selectedOrganization == null) {
        return false;
      }
      //is admin of currently selected org
      const orgMatch = account.organizations.find(
        (org) => org.organization.pk === this.selectedOrganization,
      );
      return orgMatch.is_admin;
    },

    //delete user
    async deleteData() {
      if (this.selectedAccount.pk == this.user.pk) {
        this.showSnackbar({
          content: this.$t("cannot_delete"),
          color: "error",
        });
        return;
      }

      let response = await this.http({
        url: `/api/user-management/${this.selectedAccount.pk}/delete-org-relation/`,
        method: "post",
        data: { organization: this.selectedOrganization },
      });
      if (response.error) {
        this.showSnackbar({
          content: this.$t("error_delete") + ":" + response.error,
          color: "error",
        });
      } else {
        this.showSnackbar({
          content: this.$t("success_delete"),
          color: "success",
        });
      }
    },

    closeEditDialog() {
      this.showEditDialog = false;
    },

    closeDialog() {
      this.showCreateDialog = false;
    },

    closeDeleteDialog() {
      this.showDeleteDialog = false;
    },

    closeSendEmailDialog() {
      this.showSendEmailDialog = false;
    },

    editItem(item) {
      this.showEditDialog = true;
      this.selectedAccount = Object.assign({}, item);
    },

    deleteItem(item) {
      this.showDeleteDialog = true;
      this.selectedAccount = Object.assign({}, item);
    },

    sendEmail(item, type) {
      this.emailType = type;
      this.showSendEmailDialog = true;
      this.selectedAccount = Object.assign({}, item);
    },

    async deleteAccount() {
      await this.deleteData();
      this.closeDeleteDialog();
      await this.fetchUsers();
    },

    async sendUserEmail() {
      if (this.emailType == "verification")
        await this.sendVerificationEmail(this.selectedAccount.pk);
      else {
        await this.sendInvitationEmail(this.selectedAccount.pk);
      }
      this.closeSendEmailDialog();
    },

    async successCreate() {
      this.closeDialog();
      await this.fetchUsers();
    },

    async successEdit() {
      this.closeEditDialog();
      await this.fetchUsers();
    },

    async sendInvitationEmail(to_pk) {
      let response = await this.http({
        url: "/api/send-invitation-email/",
        method: "post",
        data: { pk: to_pk },
      });
      if (response.error) {
        this.showSnackbar({
          content: this.$t("error_send_invitation") + ":" + response.error,
          color: "error",
        });
      } else {
        this.showSnackbar({
          content: this.$t("success_send_invitation"),
          color: "success",
        });
      }
    },

    async sendVerificationEmail(to_pk) {
      let response = await this.http({
        url: "/api/send-verification-email/",
        method: "post",
        data: { pk: to_pk },
      });
      if (response.error) {
        this.showSnackbar({
          content: this.$t("error_send_verification") + ":" + response.error,
          color: "error",
        });
      } else if (
        response.response.data.verification_status === "already verified"
      ) {
        this.showSnackbar({
          content: this.$t("already_verified"),
          color: "info",
        });
      } else {
        this.showSnackbar({
          content: this.$t("success_send_verification"),
          color: "success",
        });
      }
    },
  },

  async created() {
    this.selectedOrganization =
      this.orgSelected.pk === -1 ? this.orgList[0].pk : this.orgSelected.pk;

    await this.fetchUsers(); // fetch all the users in the beginning
  },
};
</script>
<style lang="scss">
.delete_info {
  font-size: 14px;
}
</style>
