<i18n lang="yaml" src="@/locales/dialog.yaml"/>
<i18n>
en:
    new_password: New password
    password_reset_header: Celus password reset
    password_reset_info: You are going to reset password for your Celus account. Fill in a new password and click "Reset".
    invitation_header: Accept Celus invitation
    invitation_info: To accept your invitation into Celus, choose a password and click "Register".
    bad_data: Sorry, this password reset link is not valid. You may have only copied a part of it or your email application messed it up.
    some_error: The attempt to change password was not successful. The link you used is either not valid or too old.
    password_reset_success: Your password was successfully reset. You can now log in {here}.
    here: here
    invitation_success: Your password was successfully set and registration completed. You can now log in {here}.
</i18n>

<template>
    <v-app>
        <v-container class="text-center">

            <v-row>
                <v-col>
                    <img src="../assets/celus-plus-white-vertical-nobg.svg" height="158" alt="Celus Logo">
                </v-col>
            </v-row>

            <template v-if="resetTokenOk && !success">
                <v-row>
                    <v-col>
                        <h2 v-text="invitation ? $t('invitation_header') : $t('password_reset_header')"></h2>
                    </v-col>
                </v-row>

                <v-row v-if="attemptFinished && error && passwordError === true" justify="center">
                    <v-alert
                            type="error"
                    >
                        {{ $t(error) }}
                    </v-alert>
                </v-row>

                <v-row>
                    <v-col>
                        <div v-text="invitation ? $t('invitation_info') : $t('password_reset_info')"></div>
                    </v-col>
                </v-row>

                <v-row justify="center">
                    <v-col cols="auto">
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
                                @click="resetPassword()"
                                :disabled="!valid"
                        >
                        </v-btn>
                    </v-col>
                </v-row>

            </template>

            <v-row v-else-if="success" justify="center">
                <v-alert
                        type="success"
                >
                    <i18n
                            :path="invitation ? 'invitation_success' : 'password_reset_success'"
                            tag="span"
                    >
                        <template #here>
                            <router-link
                                    :to="{name: 'dashboard'}"
                                    v-text="$t('here')"
                                    class="font-weight-black white--text"
                            >
                            </router-link>
                        </template>
                    </i18n>
                </v-alert>
            </v-row>

            <v-row v-else justify="center"> <!-- the token data is not OK -->
                <v-alert
                        type="error"
                >
                    {{ $t('bad_data') }}
                </v-alert>
            </v-row>
        </v-container>
    </v-app>
</template>

<script>
  import axios from 'axios'

  export default {
    name: 'PasswordResetPage',

    data () {
      return {
        invitation: this.$route.meta.invitation,
        uid: this.$route.query.uid,
        token: this.$route.query.token,
        error: null,
        errorObj: null,
        password: '',
        showPassword: false,
        rules: {
          required: value => !!value || this.$t('required'),
          min: v => v.length >= 8 || this.$t('min_pwd_length'),
        },
        success: false,
        attemptFinished: false, // was attempt to reset made?
      }
    },

    computed: {
      passwordError () {
        if (this.errorObj && !this.passwordEdited) {
          if (this.errorObj.response.data && this.errorObj.response.data.new_password2) {
            return this.errorObj.response.data.new_password2[0]
          }
        }
        return true
      },
      valid () {
        return (this.password && this.password.length >= 8)
      },
      resetTokenOk () {
        return (this.uid && this.token)
      }
    },

    methods: {
      async resetPassword () {
        this.errorObj = null
        this.error = null
        try {
          await axios.post(
            `/api/rest-auth/password/reset/confirm/`,
            {
              uid: this.uid,
              token: this.token,
              new_password1: this.password,
              new_password2: this.password
            },
            {privileged: true})
          this.success = true
        } catch (error) {
          this.errorObj = error
          this.error = 'some_error'
        } finally {
          this.attemptFinished = true
        }
      },
    },
  }
</script>
