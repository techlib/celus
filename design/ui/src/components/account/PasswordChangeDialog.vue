<i18n lang="yaml" src="@/locales/dialog.yaml" />

<i18n lang="yaml">
en:
  password_change: Password change
  new_password: New password
  change_success: Password was successfully changed
  change_password: Change password

cs:
  password_change: Změna hesla
  new_password: Nové heslo
  change_success: Heslo bylo úspěšně změněno
  change_password: Změnit heslo
</i18n>

<template>
  <v-dialog v-model="show" max-width="400px">
    <v-form :value="valid" ref="form" @submit.prevent="doChange()">
      <v-card>
        <v-card-title class="headline">{{
          $t("password_change")
        }}</v-card-title>
        <v-card-text>
          <v-text-field
            v-model="password"
            :label="$t('new_password')"
            :rules="[error, rules.required, rules.min]"
            :type="showPassword ? 'text' : 'password'"
            :append-icon="showPassword ? 'fa-eye' : 'fa-eye-slash'"
            @click:append="showPassword = !showPassword"
            counter
          ></v-text-field>
        </v-card-text>
        <v-card-actions class="pa-6">
          <v-spacer></v-spacer>
          <v-btn color="secondary" @click="show = false" v-text="$t('cancel')">
          </v-btn>
          <v-btn
            color="primary"
            :disabled="!valid || requestInProgress"
            v-text="$t('change_password')"
            type="submit"
          ></v-btn>
        </v-card-actions>
      </v-card>
    </v-form>
  </v-dialog>
</template>
<script>
import { mapActions } from "vuex";
import formRulesMixin from "@/mixins/formRulesMixin";

export default {
  name: "PasswordChangeDialog",

  mixins: [formRulesMixin],

  props: {
    value: {},
  },

  data() {
    return {
      password: "",
      showPassword: false,
      passwordEdited: false,
      requestInProgress: false, // if a request was just sent to the backend and is processed
      changeError: null,
      show: this.value,
    };
  },

  computed: {
    valid() {
      return this.password.length >= 8;
    },
    error() {
      if (this.changeError && !this.passwordEdited) {
        console.log(this.changeError.response);
        if (
          this.changeError.response.data &&
          this.changeError.response.data.new_password2
        ) {
          return this.changeError.response.data.new_password2[0];
        }
      }
      return true;
    },
  },

  methods: {
    ...mapActions({
      login: "login",
      signup: "signup",
      changePassword: "changePassword",
      showSnackbar: "showSnackbar",
    }),
    resetForm() {
      this.password = "";
      this.showPassword = false;
      this.passwordEdited = false;
      this.requestInProgress = false;
      if (this.$refs.form) {
        // on first access, the form is not yet rendered
        this.$refs.form.resetValidation();
      }
    },
    async doChange() {
      this.requestInProgress = true;
      this.passwordEdited = false;
      this.changeError = null;
      try {
        await this.changePassword({ password: this.password });
        this.showSnackbar({
          content: this.$t("change_success"),
          color: "success",
        });
        this.$emit("input", false);
      } catch (error) {
        this.changeError = error;
      } finally {
        this.requestInProgress = false;
      }
    },
  },

  watch: {
    password() {
      this.passwordEdited = true;
    },

    show() {
      this.$emit("input", this.show);
      if (this.show) {
        this.resetForm();
      }
    },

    value() {
      this.show = this.value;
    },
  },
};
</script>
<style lang="scss">
.v-select.v-text-field.short input {
  max-width: 0;
}

div.small {
  font-size: 80%;
}
</style>
