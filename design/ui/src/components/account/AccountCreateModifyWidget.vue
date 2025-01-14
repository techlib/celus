<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml" src="@/locales/dialog.yaml"></i18n>
<i18n lang="yaml">
en:
  admin_privileges: Grant admin privileges
  create_new_user: Create a new user
  edit_user: Edit user
  error_edit: Error while editing user
  error_create: Error while creating user
  user_already_exists: User with this email already exists.
  invite_link: Send an invitation link to the specified e-mail address.
  success_create: User was successfully created
  success_edit: User was successfully edited
cs:
  admin_privileges: Administrátorská oprávnění
  create_new_user: Vytvořit nového uživatele
  edit_user: Upravit uživatele
  error_edit: Při úpravě uživatele došlo k chybě
  error_create: Při vytváření uživatele došlo k chybě
  user_already_exists: Užvatel s tímto emailem již existuje.
  invite_link: Poslat pozvánku na zadanou e-mailovou adresu.
  success_create: Uživatel byl úspěšně vytvořen
  success_edit: Uživatel byl úspěšně upraven
</i18n>

<template>
  <div>
    <v-card>
      <v-card-title class="ml-3">
        {{ editMode ? $t("edit_user") : $t("create_new_user") }}
      </v-card-title>
      <v-card-text>
        <v-form v-model="valid" ref="form">
          <v-container class="pb-0">
            <v-row>
              <v-col cols="12" sm="6" md="4">
                <v-text-field
                  :label="$t('labels.email')"
                  v-model="email"
                  :rules="[rules.email, emailAlreadyExists]"
                  required
                />
              </v-col>
              <v-col cols="12" sm="6" md="4">
                <v-text-field
                  v-model="firstname"
                  :label="$t('labels.first_name')"
                  :rules="[rules.required]"
                  required
                />
              </v-col>
              <v-col cols="12" sm="6" md="4">
                <v-text-field
                  v-model="lastname"
                  :label="$t('labels.last_name')"
                  :rules="[rules.required]"
                  required
                />
              </v-col>
            </v-row>
            <v-row>
              <v-col cols="12" sm="6" md="6">
                <v-select
                  v-if="!selfEdit"
                  v-model="organization"
                  :label="$t('labels.organization')"
                  :items="organizationList"
                  item-value="pk"
                  item-text="name"
                  :disabled="true"
                >
                </v-select>
              </v-col>
              <v-col cols="12" sm="6" md="6">
                <v-checkbox
                  v-if="!selfEdit"
                  v-model="isAdmin"
                  :label="$t('admin_privileges')"
                ></v-checkbox>
              </v-col>
            </v-row>
            <v-row v-if="!editMode">
              <v-col>
                <v-checkbox v-model="sendEmail" :label="$t('invite_link')">
                </v-checkbox>
              </v-col>
            </v-row>
            <v-row>
              <v-col class="d-flex">
                <v-spacer />
                <v-btn @click="cancelEdit()" class="mr-2">
                  {{ $t("actions.cancel") }}
                </v-btn>
                <v-btn :disabled="!valid" @click="submit()" color="primary">
                  <v-icon small class="mr-2">fa-save</v-icon>
                  {{ $t("actions.save") }}
                </v-btn>
              </v-col>
            </v-row>
          </v-container>
        </v-form>
      </v-card-text>
    </v-card>
  </div>
</template>

<script>
import cancellation from "@/mixins/cancellation";
import formRulesMixin from "@/mixins/formRulesMixin";
import { mapActions, mapState } from "vuex";

export default {
  name: "AccountCreateModifyWidget",
  mixins: [cancellation, formRulesMixin],
  props: {
    organizationList: { required: false, type: Array },
    selectedOrganization: { required: false, type: Number },
    account: { required: false, type: Object },
    editMode: { required: true, type: Boolean },
  },
  data() {
    return {
      email: "",
      firstname: "",
      lastname: "",
      isAdmin: false,
      organization: this.selectedOrganization,
      valid: false,
      sendEmail: false,
      existingEmails: [],
    };
  },
  emits: ["cancel", "success", "send_email"],

  computed: {
    ...mapState({
      user: "user",
    }),

    selfEdit() {
      return this.account?.pk === this.user.pk;
    },

    userData() {
      let data = {
        first_name: this.firstname,
        last_name: this.lastname,
        email: this.email,
      };
      if (!this.selfEdit) {
        data.is_admin = this.isAdmin;
        data.organization = this.organization;
      }
      return data;
    },
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),

    checkEmailExists(response) {
      if (
        response.status === 400 &&
        (!!response.data.username || !!response.data.email)
      ) {
        this.existingEmails.push(this.email.toLowerCase());
        this.showSnackbar({
          content: this.$t("user_already_exists"),
          color: "error",
        });
        return true;
      }
      return false;
    },

    async postData() {
      let response = await this.http({
        url: "/api/user-management/",
        method: "post",
        data: this.userData,
        dontShowError: true,
      });
      if (response.error) {
        console.log(response.error);
        if (!this.checkEmailExists(response.error.response)) {
          this.showSnackbar({
            content: this.$t("error_create") + "" + response.error,
            color: "error",
          });
        }
      } else {
        this.showSnackbar({
          content: this.$t("success_create"),
          color: "success",
        });
        this.$emit("success");
        if (this.sendEmail) {
          this.$emit("send_email", response.response.data.pk);
        }
      }
    },

    async putData() {
      let response = await this.http({
        url: `/api/user-management/${this.account.pk}/`,
        method: "put",
        data: this.userData,
        dontShowError: true,
      });
      if (response.error) {
        if (!this.checkEmailExists(response.error.response)) {
          this.showSnackbar({
            content: this.$t("error_edit") + "" + response.error,
            color: "error",
          });
        }
      } else {
        this.showSnackbar({
          content: this.$t("success_edit"),
          color: "success",
        });
        this.$emit("success");
      }
    },

    cancelEdit() {
      this.$emit("cancel");
    },

    accountObjectToData() {
      if (this.account) {
        this.email = this.account.email;
        this.firstname = this.account.first_name;
        this.lastname = this.account.last_name;
        if (!this.selfEdit && this.editMode) {
          this.isAdmin = this.getIsAdmin(this.account);
        }
      }
    },

    getIsAdmin(account) {
      const orgMatch = account.organizations.find(
        (org) => org.organization.pk === this.selectedOrganization
      );
      return orgMatch.is_admin;
    },

    submit() {
      this.account ? this.putData() : this.postData();
    },

    emailAlreadyExists() {
      const email = this.email.toLowerCase();
      return (
        !this.existingEmails.includes(email) || this.$t("user_already_exists")
      );
    },
  },

  watch: {
    existingEmails() {
      this.$refs.form.validate();
    },
    account: {
      async handler() {
        this.accountObjectToData();
      },
      immediate: true,
    },
  },
};
</script>
