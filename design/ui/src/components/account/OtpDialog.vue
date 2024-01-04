<i18n lang="yaml" src="@/locales/dialog.yaml" />

<i18n lang="yaml">
en:
  verification_code_title: Two phase authentication
  verification_code_text: For extra protection of your account, please enter the verification code we just sent you to "{email}" ({codeId}).
  code_id: request ID {codeId}
  login_another_user: Login as another user
  verify_code: Verify code
  code: code
  failed_to_generate: Failed to generate verification code.
  wrong_code: The code you entered is not valid.
  resend_verification_code: Resend email
  verification_email_successfully_sent: Verification email was successfully sent.
cs:
  verification_code_title: Dvoufázová autentizace
  verification_code_text: Pro extra ochranu vašeho účtu, vložte prosím ověřovací kód, který jsme vám právě poslali na "{email}" ({codeId}).
  code_id: ID žádosti {codeId}
  login_another_user: Přihlásit jiného uživatele
  verify_code: Ověřit kód
  code: kód
  failed_to_generate: Nepodařilo se vytvořit kód.
  wrong_code: Kód, který byl použit není platný.
  resend_verification_code: Znovu poslat
</i18n>

<template>
  <v-dialog v-model="otpRequired" persistent max-width="520">
    <v-form>
      <v-card>
        <v-card-title class="headline">{{
          $t("verification_code_title")
        }}</v-card-title>
        <v-card-text>
          <div>
            <i18n path="verification_code_text">
              <template #email>
                <span class="font-weight-medium">{{ email.email }}</span>
              </template>
              <template #codeId>
                <span class="caption">{{
                  $t("code_id", { codeId: codeRequestId })
                }}</span>
              </template>
            </i18n>
          </div>

          <div v-if="codeRequestId">
            <div class="d-flex pt-6">
              <v-otp-input
                v-model="code"
                :label="$t('code')"
                type="number"
              ></v-otp-input>
              <v-btn
                color="primary"
                class="ma-3"
                v-text="$t('verify_code')"
                type="submit"
                :disabled="working || !codeRequestId || code.length != 6"
                @click="verifyCode"
              ></v-btn>
            </div>
          </div>

          <v-alert
            v-if="genError"
            type="error"
            outlined
            icon="fas fa-exclamation-circle"
          >
            {{ $t("failed_to_generate") }}
          </v-alert>

          <v-alert
            v-if="codeError"
            type="error"
            outlined
            icon="fas fa-exclamation-circle"
          >
            {{ $t("wrong_code") }}
          </v-alert>
        </v-card-text>
        <v-card-actions>
          <v-btn
            color="success"
            class="ma-3"
            :disabled="working || !codeRequestId"
            @click="sendCodeViaEmail()"
          >
            <v-icon small class="me-2">fas fa-envelope</v-icon>
            {{ $t("resend_verification_code") }}
          </v-btn>
          <v-spacer></v-spacer>
          <v-btn class="ma-3" type="submit" @click="logout" :disabled="working">
            <v-icon small class="me-2">fa fa-user</v-icon>
            {{ $t("login_another_user") }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-form>
    <!-- this dialog is shown outside of the normal layout, so it needs its own snackbar -->
    <v-snackbar v-model="snackbar.show" :color="snackbar.color">
      {{ snackbar.content }}
    </v-snackbar>
  </v-dialog>
</template>
<script>
import cancellation from "@/mixins/cancellation";
import { mapActions, mapState } from "vuex";
import formRulesMixin from "@/mixins/formRulesMixin";

export default {
  name: "OtpDialog",

  mixins: [cancellation, formRulesMixin],

  props: {
    value: {},
  },
  data() {
    return {
      code: "",
      codeError: false,
      genError: false,
      codeRequestId: null,
      working: false,
      snackbar: {
        show: false,
        content: "",
        color: "",
      },
    };
  },

  computed: {
    ...mapState({
      otpRequired: "otpRequired",
    }),
    mailDevices() {
      // Currently we support only email devices
      return (this.otpRequired || []).filter((e) => "email" in e);
    },
    email() {
      return this.mailDevices.length > 0 ? this.mailDevices[0] : {};
    },
  },

  methods: {
    ...mapActions({
      logout: "logout",
      finishAuthentication: "finishAuthentication",
    }),
    async sendCodeViaEmail() {
      this.genError = false;
      this.codeError = false;
      this.working = true;
      let response = await this.http({
        url: `/api/otp/${this.email.pk}/generate/`,
        method: "post",
        privileged: true,
        dontShowError: true,
      });
      if (response.error) {
        this.genError = true;
      } else {
        this.codeRequestId = response.response.data.request_id;
        this.snackbar = {
          show: true,
          content: this.$t("verification_email_successfully_sent"),
          color: "success",
        };
      }
      this.working = false;
    },
    async verifyCode() {
      this.codeError = false;
      this.genError = false;
      this.working = true;
      let response = await this.http({
        url: `/api/otp/${this.email.pk}/verify/`,
        method: "post",
        data: { code: this.code },
        privileged: true,
        dontShowError: true,
      });
      if (response.error) {
        this.codeError = true;
      } else {
        // Code was verified successfully -> finish authentication
        this.finishAuthentication();
      }
      this.working = false;
    },
  },

  async mounted() {
    if (this.mailDevices.length > 0) {
      await this.sendCodeViaEmail(this.mailDevices[0].pk);
    }
  },

  watch: {
    code() {
      // automatically send the code if it's complete
      // this is especially effective when the user pastes the code
      if (this.code.length === 6 && !this.working && this.codeRequestId) {
        this.verifyCode();
      }
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
