<!--

TODO:

- without being logged in, the locale is set to default and thus I get czech error messages :(

-->

<i18n lang="yaml" src="@/locales/dialog.yaml"/>

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
    how_to_gain_access: To gain or renew access to this Celus installation, let us know at <a href="mailto:ask@celus.net">ask@celus.net</a>
    signup: "Don't have an account yet? {register_here}"
    register: Register here!
    just_registering: Register
    just_registering_text: "Registration is quick and completely free - just fill in your email address and pick a (strong) password."
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
    email_required: Please enter a valid email address

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
    how_to_gain_access: Pokud chcete získat nebo obnovit přístup k tomuto systému, napište nám na <a href="mailto:ask@celus.net">ask@celus.net</a>
    signup: "Ještě nemáte účet? {register_here}"
    register: Zaregistrujte se!
    just_registering: Registrace
    just_registering_text: "Registrace je rychlá a zcela zdarma - stačí vyplnit email a vybrat si (silné) heslo."
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
    email_required: Zadejte platnou emailovou adresu
</i18n>

<template>
    <v-dialog v-model="showLoginDialog" persistent :max-width="usesPasswordLogin ? 480 : 290">

        <!-- login-->
        <v-card v-if="usesPasswordLogin && currentTab == 'login'">
            <v-card-title class="headline">{{ $t('not_logged_in') }}</v-card-title>
            <v-card-text>
                <div>{{ $t('not_logged_in_internal_text') }}</div>

                <v-alert
                        v-if="allowSignUp"
                        color="primary"
                        outlined
                        class="mt-3"
                >
                    <v-icon class="pr-3">far fa-hand-point-right</v-icon>
                    <i18n path="signup" tag="span" class="text--secondary">
                        <template #register_here>
                            <a @click="currentTab = 'register'" v-text="$t('register')"></a>
                        </template>
                    </i18n>
                </v-alert>

                <v-divider class="my-3"></v-divider>
                <v-text-field
                        v-model="email"
                        :label="$t('email')"
                        :rules="[emailError, rules.required, rules.email]"
                ></v-text-field>
                <v-text-field
                        v-model="password"
                        :label="$t('password')"
                        :rules="[passwordError, rules.required, rules.min]"
                        :type="showPassword ? 'text' : 'password'"
                        :append-icon="showPassword ? 'fa-eye' : 'fa-eye-slash'"
                        @click:append="showPassword = !showPassword"
                ></v-text-field>

                <v-alert
                        v-if="loginError"
                        type="error"
                        outlined
                        icon="fas fa-exclamation-circle"
                >
                    {{ $t('login_error') }}: "<em>{{ loginErrorText }}</em>"
                    <p v-if="!allowSignUp" class="mt-4" v-html="$t('how_to_gain_access')"></p>

                </v-alert>
            </v-card-text>
            <v-card-actions>
                <div class="ml-4" :class="{small: !loginError}">
                    <v-icon
                            color="warning"
                            class="mr-2"
                            v-if="loginError"
                    >
                        fa fa-caret-right
                    </v-icon>

                    <i18n path="password_reset.switch" tag="span" :class="loginError ? 'warning--text' : 'secondary--text'">
                        <template #reset_here>
                            <a @click="currentTab = 'reset-password'" v-text="$t('password_reset.link')"></a>
                        </template>
                    </i18n>

                    <v-icon
                            color="warning"
                            class="ml-2"
                            v-if="loginError"
                    >
                        fa fa-caret-left
                    </v-icon>
                </div>
                <v-spacer></v-spacer>
                <v-btn
                        color="primary"
                        class="ma-3"
                        @click="doLogin"
                        :disabled="!loginValid || requestInProgress"
                        v-text="$t('login')"
                ></v-btn>
            </v-card-actions>
        </v-card>
        <!-- registration -->
        <v-card v-else-if="usesPasswordLogin && currentTab == 'register'">
            <v-card-title class="headline">{{ $t('just_registering') }}</v-card-title>
            <v-card-text>
                <div v-text="$t('just_registering_text')"></div>

                <v-alert
                        v-if="allowSignUp"
                        color="primary"
                        outlined
                        class="mt-3"
                >
                    <v-icon class="pr-3">far fa-hand-point-right</v-icon>
                    <i18n path="login_from_register" tag="span" class="text--secondary">
                        <template #login_here>
                            <a @click="currentTab = 'login'" v-text="$t('login_link')"></a>
                        </template>
                    </i18n>
                </v-alert>

                <v-divider class="my-3"></v-divider>
                <v-text-field
                        v-model="email"
                        :label="$t('email')"
                        :rules="[emailError, rules.required, rules.email]"
                ></v-text-field>
                <v-text-field
                        v-model="password"
                        :label="$t('new_password')"
                        :rules="[passwordError, rules.required, rules.min]"
                        :type="showPassword ? 'text' : 'password'"
                        :append-icon="showPassword ? 'fa-eye' : 'fa-eye-slash'"
                        @click:append="showPassword = !showPassword"
                        counter
                ></v-text-field>
                <!--v-text-field v-model="password2" type="password" :label="$t('password2')"></v-text-field-->

                <v-alert
                        v-if="signupError && !emailError && !passwordError && !emailEdited && !passwordEdited"
                        type="error"
                        outlined
                        icon="fas fa-exclamation-circle"
                >
                    {{ $t('signup_error') }}: "<em>{{ signupError }}</em>"
                </v-alert>
            </v-card-text>
            <v-card-actions class="pa-6">
                <v-spacer></v-spacer>
                <v-btn
                        color="primary"
                        @click="doSignUp"
                        :disabled="!signupValid || requestInProgress"
                >{{ $t('create_account') }}</v-btn>
            </v-card-actions>
        </v-card>
        <!-- reset password -->
        <v-card v-else-if="usesPasswordLogin && currentTab == 'reset-password'">
            <v-card-title class="headline">{{ $t('password_reset.title') }}</v-card-title>
            <v-card-text>
                <div>{{ $t('password_reset.text') }}</div>

                <v-text-field
                        v-model="email"
                        :label="$t('email')"
                        :rules="[emailError, rules.required, rules.email]"
                        class="mt-6"
                ></v-text-field>
                <v-alert
                        v-if="resetError"
                        type="error"
                        outlined
                        icon="fas fa-exclamation-circle"
                >
                    {{ $t('password_reset.error') }}: "<em>{{ resetError }}</em>"
                </v-alert>
                <v-alert
                        v-if="resetSuccess"
                        type="success"
                        outlined
                >
                    <i18n path="password_reset.success" tag="span" class="text--secondary">
                        <template #reset_email>
                            <a :href="'mailto:' + email" v-text="email"></a>
                        </template>
                    </i18n>
                </v-alert>
            </v-card-text>
            <v-card-actions>
                <div class="ml-4 small">
                    <i18n path="password_reset.back_to_login" tag="span" class="text--secondary">
                        <template #login>
                            <a @click="currentTab = 'login'; resetForm()" v-text="$t('login')"></a>
                        </template>
                    </i18n>
                </div>
                <v-spacer></v-spacer>
                <v-btn
                        color="primary"
                        class="ma-3"
                        @click="doReset()"
                        :disabled="!resetValid || requestInProgress"
                        v-if="!resetSuccess"
                        v-text="$t('password_reset.button')"
                ></v-btn>
                <v-btn
                        v-else
                        @click="currentTab = 'login'; resetForm()"
                        v-text="$t('password_reset.back_to_login_full')"
                        class="mr-4 mb-3"
                        color="primary"
                ></v-btn>
            </v-card-actions>
        </v-card>
        <!-- SSO -->
        <v-card v-else>
            <v-card-title class="headline">{{ $t('not_logged_in') }}</v-card-title>
            <v-card-text>{{ $t('not_logged_in_external_text') }}</v-card-text>
            <v-card-actions>
                <v-spacer></v-spacer>
                <v-btn color="primary" text :href="$route.path + '?t=' + currentTimestamp">{{ $t('login') }}</v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>
</template>
<script>
  import { mapActions, mapGetters, mapState } from 'vuex'

  export default {
    name: 'LoginDialog',
    props: {
      value: {},
    },
    data () {
      return {
        email: '',
        password: '',
        password2: '',
        currentTab: 'register' in this.$route.query ? 'register' : ('reset-password' in this.$route.query ? 'reset-password' : 'login'),
        rules: {
          required: value => !!value || this.$t('required'),
          min: v => v.length >= 8 || this.$t('min_pwd_length'),
          email: v => !!v.match(/^.+@.+\...+/) || this.$t('email_required')
        },
        signupError: null,
        resetError: null,
        showPassword: false,
        emailEdited: false,  // when email gets edited, we hide associated error message
        passwordEdited: false,
        requestInProgress: false,  // if a request was just sent to the backend and is processed
        resetSuccess: false, // reset email was sent
      }
    },
    computed: {
      ...mapState({
        loginError: state => state.login.loginError,

      }),
      ...mapGetters({
        loginErrorText: 'loginErrorText',
        allowSignUp: 'allowSignUp',
        usesPasswordLogin: 'usesPasswordLogin',
      }),
      showLoginDialog: {
        get () {
          return this.$store.state.showLoginDialog
        },
        set (newValue) {
          this.$store.dispatch('setShowLoginDialog', {show: newValue})
        }
      },
      currentTimestamp () {
        // we add the current timestamp param to the URL in order to unsure the
        // page will not be fetched from cache by the browser
        return new Date().getTime()
      },
      signupValid () {
        return (this.email !== '' && this.rules.email(this.email) === true && this.password.length >= 8)
      },
      loginValid () {
        return (this.email !== '' && this.rules.email(this.email) === true && this.password.length >= 8)
      },
      resetValid () {
        return this.email !== '' && this.rules.email(this.email) === true
      },
      emailError () {
        if (this.signupError && !this.emailEdited) {
          if (this.signupError.response.data && this.signupError.response.data.email) {
            return this.signupError.response.data.email[0]
          }
        }
        return true
      },
      passwordError () {
        if (this.signupError && !this.passwordEdited) {
          if (this.signupError.response.data && this.signupError.response.data.password1) {
            return this.signupError.response.data.password1[0]
          }
        }
        return true
      },
    },

    methods: {
      ...mapActions({
        login: 'login',
        signup: 'signup',
        resetPassword: 'resetPassword',
        showSnackbar: 'showSnackbar',
      }),
      resetForm () {
        this.resetError = null
        this.resetSuccess = false
        this.signupError = null
        this.password = ''
        this.showPassword = false
        this.passwordEdited = false
        this.requestInProgress = false
        this.$store.state.login.loginError = null
      },
      async doLogin () {
        this.requestInProgress = true
        try {
          await this.login({email: this.email, password: this.password})
        } finally {
          this.requestInProgress = false
        }
      },
      async doSignUp () {
        this.requestInProgress = true
        try {
          await this.signup({email: this.email, password1: this.password, password2: this.password})
          this.showSnackbar({content: 'Signup ok', color: 'success'})
        } catch (error) {
          this.emailEdited = false
          this.passwordEdited = false
          this.signupError = error
        } finally {
          this.requestInProgress = false
        }
      },
      async doReset () {
        this.requestInProgress = true
        this.resetError = null
        this.resetSuccess = false
        try {
          await this.resetPassword({email: this.email})
          this.resetSuccess = true
        } catch (error) {
          console.log(error)
          this.resetError = error
        } finally {
          this.requestInProgress = false
        }
      },
      processError (error) {
        let data = error.response.data
        if ('email' in data) {

        }
      }
    },

    watch: {
      email () {
        this.emailEdited = true
      },
      password () {
        this.passwordEdited = true
      }
    },

  }
</script>
<style lang="scss">

    .v-select.v-text-field.short input {
        max-width: 0;
    }

    div.small {
      font-size: 80%
    }

</style>
