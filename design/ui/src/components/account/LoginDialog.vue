<i18n lang="yaml" src="@/locales/dialog.yaml"></i18n>

<i18n lang="yaml">
en:
  not_logged_in: Login
  not_logged_in_internal_text: Please enter your login credentials and click "Login".
  not_logged_in_external_text: You are not logged in, probably because you have been logged out due to inactivity. Please click "Login" to be redirected to login page.
  login: Login
  email: Email
  password: Password
  new_password: Choose a password
  password2: Repeat password
  login_error: There was an error logging you in
  signup: "Don't have an account yet? {register_here}"
  register: Register here!
  just_registering: Register
  just_registering_text: "Registration is quick and completely free - just fill in your email address and pick a (strong) password."
  just_registering_given_email_text: "Registration is quick and completely free - just pick a (strong) password."
  password_reset:
    title: Reset password
    text: Enter a valid email address which was used during registration. We will send you a link for password recovery to this address.
    switch: "Forgotten password? {reset_here}"
    link: Reset it here.
    back_to_login: Back to {login}.
    back_to_login_full: Back to login
    login: login
    error: An error occured during password reset
    success: An email to reset password was sent to {reset_email}.
    button: Send recovery link
  create_account: Create account
  login_from_register: "Already have account? {login_here}"
  login_link: Login here.
  signup_error: Error during sign-up

cs:
  not_logged_in: Přihlášení
  not_logged_in_internal_text: Zadejte své přihlašovací údaje a stiskněte "Přihlásit".
  not_logged_in_external_text: Pravděpodobně jste byli odhlášeni z důvodu neaktivity. Prosím stiskněte "Přihlásit" pro opětovné přihlášení.
  login: Přihlásit
  email: Email
  password: Heslo
  new_password: Zvolte si heslo
  password2: Potvrzení hesla
  login_error: Při přihlášování došlo k chybě
  signup: "Ještě nemáte účet? {register_here}"
  register: Zaregistrujte se!
  just_registering: Registrace
  just_registering_text: "Registrace je rychlá a zcela zdarma - stačí vyplnit email a vybrat si (silné) heslo."
  just_registering_given_email_text: "Registrace je rychlá a zcela zdarma - stačí vybrat si (silné) heslo."
  password_reset:
    title: Obnova hesla
    text: Zadejte platnou emailovou adresu, kterou jste použili při registraci. Pošleme vám na ni odkaz, pomocí kterého můžete provést změnu hesla.
    switch: "Zapomenuté heslo? {reset_here}"
    link: Obnovit zde.
    back_to_login: Zpět na {login}.
    back_to_login_full: Zpět na přihlášení
    login: přihlášení
    error: Během resetování hesla došlo k chybě
    success: E-mail pro obnovu hesla byl odeslán na {reset_email}.
    button: Odeslat odkaz pro obnovení
  create_account: Vytvořit účet
  login_from_register: "Již máte účet? {login_here}"
  login_link: Přihlašte se zde.
  signup_error: Chyba při vytváření účtu
</i18n>

<template>
  <v-dialog
    v-model="showLoginDialog"
    persistent
    :max-width="usesPasswordLogin ? 480 : 290"
  >
    <!-- login-->
    <v-form
      v-if="usesPasswordLogin && currentTab == 'login'"
      v-model="valid"
      @submit.prevent="doLogin"
    >
      <v-card>
        <v-card-title class="headline">{{ $t("not_logged_in") }}</v-card-title>
        <v-card-text class="pb-0">
          <div class="title_description text-disabled">
            {{ $t("not_logged_in_internal_text") }}
          </div>
          <v-alert
            v-if="allowSignUp"
            color="primary"
            variant="outlined"
            class="mt-3"
          >
            <v-icon class="mr-3" size="small">far fa-question-circle</v-icon>
            <i18n-t keypath="signup" tag="span" class="text--secondary">
              <template #register_here>
                <a
                  v-if="externalRegistrationUrl"
                  :href="externalRegistrationUrl"
                  v-text="$t('register')"
                ></a>
                <a
                  v-else
                  @click="currentTab = 'register'"
                  v-text="$t('register')"
                ></a>
              </template>
            </i18n-t>
          </v-alert>
          <v-divider class="my-3"></v-divider>
          <v-text-field
            v-model="email"
            :label="$t('email')"
            :rules="[emailError, rules.required, rules.email]"
            :disabled="emailGiven"
          ></v-text-field>
          <v-text-field
            v-model="password"
            :label="$t('password')"
            :rules="[passwordError, rules.required, rules.min]"
            :type="showPassword ? 'text' : 'password'"
          >
            <template #append-inner>
              <v-icon
                @click="showPassword = !showPassword"
                v-if="showPassword"
                size="x-small"
                icon="fa fa-eye"
              ></v-icon>
              <v-icon
                @click="showPassword = !showPassword"
                v-else
                size="x-small"
                icon="fa fa-eye-slash"
              ></v-icon>
            </template>
          </v-text-field>
          <v-alert
            v-if="loginError"
            type="error"
            variant="outlined"
            icon="fa fa-exclamation-circle"
          >
            {{ $t("login_error") }}: "<em>{{ loginErrorText }}</em
            >"
          </v-alert>
        </v-card-text>
        <v-card-actions>
          <div class="ml-4" :class="{ small: !loginError }">
            <v-icon color="warning" class="mr-2" v-if="loginError">
              fa fa-caret-right
            </v-icon>
            <i18n-t
              keypath="password_reset.switch"
              tag="span"
              :class="loginError ? 'text-warning' : 'text-secondary'"
            >
              <template #reset_here>
                <a
                  @click="currentTab = 'reset-password'"
                  v-text="$t('password_reset.link')"
                ></a>
              </template>
            </i18n-t>
            <v-icon color="warning" class="ml-2" v-if="loginError">
              fa fa-caret-left
            </v-icon>
          </div>
          <v-spacer></v-spacer>
          <v-btn
            color="primary"
            class="ma-3"
            :disabled="!valid || requestInProgress"
            type="submit"
            variant="elevated"
            >{{ $t("login") }}</v-btn
          >
        </v-card-actions>
      </v-card>
    </v-form>
    <!-- registration -->
    <v-form
      v-else-if="usesPasswordLogin && currentTab == 'register'"
      v-model="valid"
      @submit.prevent="doSignUp"
    >
      <v-card>
        <v-card-title class="headline">{{
          $t("just_registering")
        }}</v-card-title>
        <v-card-text>
          <div
            v-text="
              emailGiven
                ? $t('just_registering_given_email_text')
                : $t('just_registering_text')
            "
          ></div>
          <v-alert
            v-if="allowSignUp"
            color="primary"
            variant="outlined"
            class="mt-3"
          >
            <v-icon class="pr-3">far fa-hand-point-right</v-icon>
            <i18n-t
              keypath="login_from_register"
              tag="span"
              class="text--secondary"
            >
              <template #login_here>
                <a @click="currentTab = 'login'" v-text="$t('login_link')"></a>
              </template>
            </i18n-t>
          </v-alert>
          <v-divider class="my-3"></v-divider>
          <v-text-field
            v-model="email"
            :label="$t('email')"
            :rules="[emailError, rules.required, rules.email]"
            :disabled="emailGiven"
          ></v-text-field>
          <v-text-field
            v-model="password"
            :label="$t('new_password')"
            :rules="[passwordError, rules.required, rules.min]"
            :type="showPassword ? 'text' : 'password'"
            :append-icon="showPassword ? 'fa fa-eye' : 'fa fa-eye-slash'"
            @click:append="showPassword = !showPassword"
            counter
          ></v-text-field>
          <!--v-text-field v-model="password2" type="password" :label="$t('password2')"></v-text-field-->
          <v-alert
            v-if="
              signupError &&
              !emailError &&
              !passwordError &&
              !emailEdited &&
              !passwordEdited
            "
            type="error"
            variant="outlined"
            icon="fa fa-exclamation-circle"
          >
            {{ $t("signup_error") }}: "<em>{{ signupError }}</em
            >"
          </v-alert>
        </v-card-text>
        <v-card-actions class="pa-6">
          <v-spacer></v-spacer>
          <v-btn
            color="primary"
            :disabled="!valid || requestInProgress"
            type="submit"
            >{{ $t("create_account") }}</v-btn
          >
        </v-card-actions>
      </v-card>
    </v-form>
    <!-- reset password -->
    <v-form
      v-else-if="usesPasswordLogin && currentTab == 'reset-password'"
      v-model="valid"
      @submit.prevent="doReset"
    >
      <v-card>
        <v-card-title class="headline">{{
          $t("password_reset.title")
        }}</v-card-title>
        <v-card-text>
          <div class="pass_text">{{ $t("password_reset.text") }}</div>
          <v-text-field
            v-model="email"
            :label="$t('email')"
            :rules="[emailError, rules.required, rules.email]"
            class="mt-6"
          ></v-text-field>
          <v-alert
            v-if="resetError"
            type="error"
            variant="outlined"
            icon="fa fa-exclamation-circle"
          >
            {{ $t("password_reset.error") }}: "<em>{{ resetError }}</em
            >"
          </v-alert>
          <v-alert v-if="resetSuccess" type="success" variant="outlined">
            <i18n-t
              keypath="password_reset.success"
              tag="span"
              class="text--secondary"
            >
              <template #reset_email>
                <a :href="'mailto:' + email" v-text="email"></a>
              </template>
            </i18n-t>
          </v-alert>
        </v-card-text>
        <v-card-actions>
          <div class="ml-4 small">
            <i18n-t
              keypath="password_reset.back_to_login"
              tag="span"
              class="text--secondary"
            >
              <template #login>
                <a
                  @click="
                    currentTab = 'login';
                    resetForm();
                  "
                  v-text="$t('login')"
                ></a>
              </template>
            </i18n-t>
          </div>
          <v-spacer></v-spacer>
          <v-btn
            color="primary"
            variant="elevated"
            class="ma-3"
            :disabled="!valid || requestInProgress"
            v-if="!resetSuccess"
            type="submit"
          >
            {{ $t("password_reset.button") }}
          </v-btn>
          <v-btn
            v-else
            @click="
              currentTab = 'login';
              resetForm();
            "
            class="mr-4 mb-3"
            color="primary"
          >
            {{ $t("password_reset.back_to_login_full") }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-form>
    <!-- SSO -->
    <v-card v-else>
      <v-card-title class="headline">{{ $t("not_logged_in") }}</v-card-title>
      <v-card-text>{{ $t("not_logged_in_external_text") }}</v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn
          color="primary"
          text
          :href="$route.path + '?t=' + currentTimestamp"
          >{{ $t("login") }}</v-btn
        >
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
import { mapActions, mapGetters, mapState } from "vuex";
import formRulesMixin from "@/mixins/formRulesMixin";

export default {
  name: "LoginDialog",

  mixins: [formRulesMixin],

  props: {
    value: {},
  },

  data() {
    const urlParams = new URLSearchParams(window.location.search);
    return {
      email: urlParams.get("email") || "",
      emailGiven: urlParams.has("email"),
      password: "",
      password2: "",
      currentTab: urlParams.has("register")
        ? "register"
        : urlParams.has("reset-password")
          ? "reset-password"
          : "login",
      signupError: null,
      resetError: null,
      showPassword: false,
      emailEdited: false, // when email gets edited, we hide associated error message
      passwordEdited: false,
      requestInProgress: false, // if a request was just sent to the backend and is processed
      resetSuccess: false, // reset email was sent
      valid: false,
    };
  },

  computed: {
    ...mapState({
      loginError: (state) => state.login.loginError,
      basicInfo: (state) => state.basicInfo,
    }),
    ...mapGetters({
      loginErrorText: "loginErrorText",
      allowSignUp: "allowSignUp",
      usesPasswordLogin: "usesPasswordLogin",
    }),
    externalRegistrationUrl() {
      return this.basicInfo.EXTERNAL_REGISTRATION_URL || "";
    },
    showLoginDialog: {
      get() {
        return this.$store.state.showLoginDialog;
      },
      set(newValue) {
        this.$store.dispatch("setShowLoginDialog", { show: newValue });
      },
    },
    currentTimestamp() {
      // we add the current timestamp param to the URL in order to unsure the
      // page will not be fetched from cache by the browser
      return new Date().getTime();
    },
    emailError() {
      if (this.signupError && !this.emailEdited) {
        if (
          this.signupError.response.data &&
          this.signupError.response.data.email
        ) {
          return this.signupError.response.data.email[0];
        }
      }
      return true;
    },
    passwordError() {
      if (this.signupError && !this.passwordEdited) {
        if (
          this.signupError.response.data &&
          this.signupError.response.data.password1
        ) {
          return this.signupError.response.data.password1[0];
        }
      }
      return true;
    },
  },

  methods: {
    ...mapActions({
      login: "login",
      signup: "signup",
      resetPassword: "resetPassword",
      showSnackbar: "showSnackbar",
    }),
    resetForm() {
      this.resetError = null;
      this.resetSuccess = false;
      this.signupError = null;
      this.password = "";
      this.showPassword = false;
      this.passwordEdited = false;
      this.requestInProgress = false;
      this.$store.state.login.loginError = null;
    },
    async doLogin() {
      this.requestInProgress = true;
      try {
        await this.login({ email: this.email, password: this.password });
      } finally {
        this.requestInProgress = false;
      }
    },
    async doSignUp() {
      this.requestInProgress = true;
      try {
        await this.signup({
          email: this.email,
          password1: this.password,
          password2: this.password,
        });
        this.showSnackbar({ content: "Signup ok", color: "success" });
      } catch (error) {
        this.emailEdited = false;
        this.passwordEdited = false;
        this.signupError = error;
      } finally {
        this.requestInProgress = false;
      }
    },
    async doReset() {
      this.requestInProgress = true;
      this.resetError = null;
      this.resetSuccess = false;
      try {
        await this.resetPassword({ email: this.email });
        this.resetSuccess = true;
      } catch (error) {
        this.resetError = error;
      } finally {
        this.requestInProgress = false;
      }
    },
  },

  watch: {
    email() {
      this.emailEdited = true;
    },
    password() {
      this.passwordEdited = true;
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

a {
  cursor: pointer;
}

.v-card-title {
  font-size: 1.5rem;
  padding: 16px;
  font-weight: 400;
}

.v-card-text {
  padding: 16px !important;
  padding-top: 0 !important;
}

.pass_text {
  color: rgba($color: #000000, $alpha: 0.6);
  font-size: 0.875rem;
  font-weight: 400;
  line-height: 1.375rem;
  letter-spacing: 0.0071428571em;
}

.title_description {
  font-size: 14px;
}
</style>
