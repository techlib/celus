<i18n lang="yaml" src="@/locales/dialog.yaml" />
<i18n lang="yaml">
en:
  messed_up: You may have only copied a part of it or your email application messed it up.
  too_old: The link you used is either not valid or too old.
  eduid_invitation:
    bad_data: Sorry, this invitation link is not valid. @:messed_up
    header: Accept CELUS invitation
    info: To accept your invitation into CELUS, click "Register".
    some_error: The attempt to register was not successful. @:too_old
    success: Registration was successful. Click {here} to enter CELUS.
  password_invitation:
    bad_data: Sorry, this invitation link is not valid. @:messed_up
    header: Accept CELUS invitation
    info: To accept your invitation into CELUS, choose a password and click "Register".
    some_error: The attempt to register was not successful. @:too_old
    success: Your password was successfully set and registration completed. You can now log in {here}.
  password_reset:
    bad_data: Sorry, this password reset link is not valid. @:messed_up
    header: CELUS password reset
    info: You are going to reset password for your CELUS account. Fill in a new password and click "Reset".
    some_error: The attempt to change password was not successful. @:too_old
    success: Your password was successfully reset. You can now log in {here}.
  here: here
  new_password: New password
  register: Register
  reset: Reset

cs:
  messed_up: Možná jste zkopírovali jen část odkazu, nebo ho váš emailový klient poškodil.
  too_old: Odkaz, který jste použili, buď není platný, nebo je příliš starý.
  eduid_invitation:
    bad_data: Je nám líto, ale tento odkaz na pozvánku není platný. @:messed_up
    header: Přijměte pozvánku do CELUSu
    info: Pro přijetí pozvánky do CELUSu klikněte na "Registrovat".
    some_error: Pokus o registraci nebyl úspěšný. @:too_old
    success: Registrace byla úspěšná. Klikněte {here}, abyste vstoupili do CELUSu.
  password_invitation:
    bad_data: Je nám líto, ale tento odkaz na pozvánku není platný. @:messed_up
    header: Přijměte pozvánku do CELUSu
    info: Pro přijetí pozvánky do CELUSu zvolte heslo a klikněte na "Registrovat".
    some_error: Pokus o registraci nebyl úspěšný. @:too_old
    success: Vaše heslo bylo úspěšně nastaveno a registrace dokončena. Nyní se můžete přihlásit {here}.
  password_reset:
    bad_data: Omlouváme se, ale tento odkaz na obnovení hesla není platný. @:messed_up
    header: Obnovení hesla do CELUSu
    info: Chystáte se obnovit heslo pro svůj účet v CELUSu. Vyplňte nové heslo a klikněte na "Obnovit".
    some_error: Pokus o změnu hesla nebyl úspěšný. @:too_old
    success: Vaše heslo bylo úspěšně změněno. Nyní se můžete přihlásit {here}.
  here: zde
  new_password: Nové heslo
  register: Registrovat
  reset: Obnovit
</i18n>

<template>
  <v-app>
    <v-container class="text-center">
      <v-row>
        <v-col>
          <img
            src="../assets/celus-plus-white-vertical-nobg.svg"
            height="158"
            alt="CELUS Logo"
          />
        </v-col>
      </v-row>

      <v-row v-if="!ready">
        <LargeSpinner />
      </v-row>

      <template v-else-if="resetTokenOk && !success">
        <v-row>
          <v-col>
            <h2 v-text="$t(scope + '.header')"></h2>
          </v-col>
        </v-row>

        <v-row
          v-if="attemptFinished && error && passwordError === true"
          justify="center"
        >
          <v-alert type="error">
            {{ $t(scope + ".some_error") }}
          </v-alert>
        </v-row>

        <v-row>
          <v-col>
            <div v-text="$t(scope + '.info')"></div>
          </v-col>
        </v-row>

        <v-row justify="center">
          <v-col cols="auto" v-if="!usesEduId">
            <v-text-field
              v-model="password"
              :label="$t('new_password')"
              :rules="[passwordError, rules.required, rules.min]"
              :type="showPassword ? 'text' : 'password'"
              :append-icon="showPassword ? 'fa-eye' : 'fa-eye-slash'"
              @click:append="showPassword = !showPassword"
              outlined
            ></v-text-field>
          </v-col>
          <v-col cols="auto">
            <v-btn
              v-text="invitation ? $t('register') : $t('reset')"
              color="primary"
              class="mt-2"
              @click="proceed()"
              :disabled="!valid"
            >
            </v-btn>
          </v-col>
        </v-row>
      </template>

      <v-row v-else-if="success" justify="center">
        <v-alert type="success">
          <i18n :path="scope + '.success'" tag="span">
            <template #here>
              <a
                href="/"
                v-text="$t('here')"
                class="font-weight-black white--text"
              >
              </a>
            </template>
          </i18n>
        </v-alert>
      </v-row>

      <v-row v-else justify="center">
        <!-- the token data is not OK -->
        <v-alert type="error">
          {{ $t(scope + ".bad_data") }}
        </v-alert>
      </v-row>
    </v-container>
  </v-app>
</template>

<script>
import axios from "axios";
import formRulesMixin from "@/mixins/formRulesMixin";
import { mapActions, mapGetters, mapState } from "vuex";
import LargeSpinner from "@/components/util/LargeSpinner.vue";
import isEmpty from "lodash/isEmpty";

export default {
  name: "PasswordResetPage",
  components: { LargeSpinner },

  mixins: [formRulesMixin],

  data() {
    return {
      invitation: this.$route.meta.invitation,
      uid: this.$route.query.uid,
      token: this.$route.query.token,
      error: false,
      errorObj: null,
      password: "",
      showPassword: false,
      success: false,
      attemptFinished: false, // was attempt to reset made?
    };
  },

  computed: {
    ...mapState(["basicInfo"]),
    usesEduId() {
      return this.basicInfo && this.basicInfo.ALLOW_EDUID_LOGIN;
    },
    ready() {
      return !isEmpty(this.basicInfo);
    },
    scope() {
      if (this.invitation) {
        if (this.usesEduId) {
          return "eduid_invitation";
        } else {
          return "password_invitation";
        }
      }
      return "password_reset";
    },
    passwordError() {
      if (this.errorObj && !this.passwordEdited) {
        if (
          this.errorObj.response.data &&
          this.errorObj.response.data.new_password2
        ) {
          return this.errorObj.response.data.new_password2[0];
        }
      }
      return true;
    },
    valid() {
      return (
        this.usesEduId ||
        (this.password && this.password.length >= this.minPasswordLength)
      );
    },
    resetTokenOk() {
      return this.uid && this.token;
    },
  },

  methods: {
    ...mapActions(["start"]),
    async proceed() {
      if (this.usesEduId) {
        await this.register();
      } else {
        await this.resetPassword();
      }
    },
    async resetPassword() {
      this.errorObj = null;
      this.error = false;
      try {
        await axios.post(
          `/api/user/password-reset`,
          {
            uid: this.uid,
            token: this.token,
            new_password1: this.password,
            new_password2: this.password,
          },
          { privileged: true }
        );
        this.success = true;
      } catch (error) {
        this.errorObj = error;
        this.error = true;
      } finally {
        this.attemptFinished = true;
      }
    },
    async register() {
      this.errorObj = null;
      this.error = false;
      try {
        await axios.post(
          `/api/user/confirm-identity/`,
          {
            uid: this.uid,
            token: this.token,
          },
          { privileged: true }
        );
        this.success = true;
      } catch (error) {
        this.errorObj = error;
        this.error = true;
      } finally {
        this.attemptFinished = true;
      }
    },
  },
};
</script>
