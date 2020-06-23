<!--

TODO:

- without being logged in, the locale is set to default and thus I get czech error messages :(

-->

<i18n lang="yaml">
en:
    not_logged_in: Login
    not_logged_in_internal_text: Please enter your login credentials and click "Login".
    not_logged_in_external_text: You are not logged in, probably because you have been logged out due to inactivity. Please click "Login" to be redirected to login page.
    login: Login
    email: Email
    password: Password
    password2: Repeat password
    login_error: There was an error logging you in
    how_to_gain_access: To gain or renew access to this Celus installation, let us know at <a href="mailto:ask@celus.net">ask@celus.net</a>
    signup: "Don't have an account yet? {register_here}"
    register: Register here!
    just_registering: Register
    just_registering_text: "Registration is quick and completely free - just fill in your email address and pick a strong password."
    create_account: Create account
    min_pwd_length: Minimum 6 characters
    required: This value cannot be empty

cs:
    not_logged_in: Přihlášení
    not_logged_in_internal_text: Zadejte své přihlašovací údaje a stiskněte "Přihlásit".
    not_logged_in_external_text: Pravděpodobně jste byli odhlášeni z důvodu neaktivity. Prosím stiskněte "Přihlásit" pro opětovné přihlášení.
    login: Přihlásit
    email: Email
    password: Heslo
    password2: Potvrzení hesla
    login_error: Při přihlášování došlo k chybě
    how_to_gain_access: Pokud chcete získat nebo obnovit přístup k tomuto systému, napište nám na <a href="mailto:ask@celus.net">ask@celus.net</a>
    signup: "Ještě nemáte účet? {register_here}"
    register: Zaregistrujte se!
    just_registering: Registrace
    just_registering_text: "Registrace je rychlá a zcela a zdarma - stačí vyplnit email a vybrat si silné heslo."
    create_account: Vytvořit účet
</i18n>

<template>
    <v-dialog v-model="showLoginDialog" persistent :max-width="usesPasswordLogin ? 480 : 290">
        <v-card v-if="usesPasswordLogin && !justRegistering">
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
                            <a @click="justRegistering = true" v-text="$t('register')"></a>
                        </template>
                    </i18n>
                </v-alert>

                <v-divider class="my-3"></v-divider>
                <v-text-field v-model="email" :label="$t('email')"></v-text-field>
                <v-text-field v-model="password" type="password" :label="$t('password')"></v-text-field>

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
                <v-spacer></v-spacer>
                <v-btn color="primary" class="ma-3" @click="doLogin">{{ $t('login') }}</v-btn>
            </v-card-actions>
        </v-card>
        <!-- just registering -->
        <v-card v-else-if="usesPasswordLogin && justRegistering">
            <v-card-title class="headline">{{ $t('just_registering') }}</v-card-title>
            <v-card-text>
                <div v-text="$t('just_registering_text')"></div>
                <v-divider class="my-3"></v-divider>
                <v-text-field
                        v-model="email"
                        :label="$t('email')"
                        :rules="[rules.required]"
                ></v-text-field>
                <v-text-field
                        v-model="password" type="password"
                        :label="$t('password')"
                        :rules="[rules.required, rules.min]"
                ></v-text-field>
                <v-text-field v-model="password2" type="password" :label="$t('password2')"></v-text-field>
            </v-card-text>
            <v-card-actions class="pa-6">
                <v-spacer></v-spacer>
                <v-btn
                        color="primary"
                        @click="doSignUp"
                        :disabled="!signupValid"
                >{{ $t('create_account') }}</v-btn>
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
  import axios from 'axios'

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
        justRegistering: false,
        rules: {
          required: value => !!value || this.$t('required'),
          min: v => v.length >= 6 || this.$t('min_pwd_length'),
        }
      }
    },
    computed: {
      ...mapState({
        usesPasswordLogin: state => state.login.usesPasswordLogin,
        loginError: state => state.login.loginError,

      }),
      ...mapGetters({
        loginErrorText: 'loginErrorText',
        allowSignUp: 'allowSignUp',
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
        return (this.email !== '' && this.password !== '' && (this.password === this.password2))
      }
    },

    methods: {
      ...mapActions({
        login: 'login',
        showSnackbar: 'showSnackbar',
      }),
      doLogin () {
        this.login({email: this.email, password: this.password})
      },
      async doSignUp () {
        console.info('Signing up')
        try {
          let result = await axios.post(
            '/api/rest-auth/registration/',
            {
              email: this.email,
              password1: this.password,
              password2: this.password2,
            },
            {privileged: true},
          )
          console.log(result)
          this.showSnackbar({content: 'Signup ok', color: 'success'})
        } catch (error) {
          console.log(error)
          if (error.response.status === 400) {
            console.log(error.response.data)
            this.showSnackbar({content: 'Something is wrong: '+error, color: 'warning'})
          } else {
            this.showSnackbar({content: 'Could not sign you up: ' + error, color: 'error'})
          }
        }
      }
    }
  }
</script>
<style lang="scss">

    .v-select.v-text-field.short input {
        max-width: 0;
    }

</style>
