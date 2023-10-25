<i18n lang="yaml">
en:
  heading: Your email is not verified
  info_text: Please verify your email address by clicking on the link in the verification email we have sent you.
  ask_for_help: In case you have trouble verifying your email, please contact us at
  email_subject: Problem with email verification
  check_again: I have verified my email
  send_again: Resend email
  resent: Verification email has been sent
  checked: Your email is still not verified
  close: Close

cs:
  heading: Váš email není ověřen
  info_text: Prosím ověřte svou e-mailovou adresu kliknutím na odkaz v e-mailu, který jsme vám poslali.
  ask_for_help: Pokud máte problém s ověřením e-mailu, kontaktujte nás na
  email_subject: Problém s ověřením emailu
  check_again: Email jsem ověřil
  send_again: Znovu poslat email
  resent: Ověřovací email byl odeslán
  checked: Váš email stále není ověřen
  close: Zavřít
</i18n>
<template>
  <v-app>
    <v-row justify="center">
      <v-dialog :value="true" persistent max-width="600">
        <v-card class="py-2">
          <v-card-title class="text-h5 mb-2">
            {{ $t("heading") }}
          </v-card-title>
          <v-card-text>
            {{ $t("info_text") }}
          </v-card-text>

          <v-card-text class="text-caption">
            <span>{{ $t("ask_for_help") }}</span
            >&nbsp;<a :href="emailLink">{{ contactEmail }}</a>
            <span>.</span>
          </v-card-text>

          <v-card-actions class="mt-2">
            <v-btn
              class="secondary"
              @click="recheckEmailVerified"
              :disabled="checking"
            >
              {{ $t("check_again") }}
            </v-btn>
            <v-spacer></v-spacer>
            <v-btn
              class="primary"
              @click="sendVerificationEmail"
              :disabled="sending"
            >
              {{ $t("send_again") }}
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>
      <v-snackbar v-model="snackbarShow" :color="snackbarColor">
        {{ snackbarText }}
        <template #action="{ attrs }">
          <v-btn dark text @click="snackbarHide" v-bind="attrs">{{
            $t("close")
          }}</v-btn>
        </template>
      </v-snackbar>
    </v-row>
  </v-app>
</template>

<script>
import { mapActions, mapGetters } from "vuex";
import axios from "axios";

export default {
  name: "EmailNotVerified",
  data() {
    return {
      checking: false,
      sending: false,
      snackbarColor: null,
      snackbarText: "",
      snackbarShow: false,
      loadUserDataInterval: null,
    };
  },
  computed: {
    ...mapGetters({
      emailVerified: "emailVerified",
      contactEmail: "contactEmail",
    }),
    emailLink() {
      return `mailto:${this.contactEmail}?subject=${this.$t("email_subject")}`;
    },
  },
  methods: {
    ...mapActions({
      loadUserData: "loadUserData",
    }),
    showSnackbar({ content, color }) {
      this.snackbarText = content;
      this.snackbarColor = color;
      this.snackbarShow = true;
    },
    snackbarHide() {
      this.snackbarShow = false;
    },
    handleError(error, message) {
      this.showSnackbar({
        content: `${message}: ${error.message}`,
        color: "error",
      });
    },

    async sendVerificationEmail(initial = false) {
      try {
        console.log("sending", initial);
        this.sending = true;
        await axios.post("/api/user/verify-email", null, { privileged: true });
        if (!initial) {
          this.showSnackbar({
            content: this.$t("resent"),
            color: "success",
          });
        }
      } catch (error) {
        this.handleError(error, "Error sending verification email");
      } finally {
        this.sending = false;
      }
    },
    async recheckEmailVerified() {
      try {
        this.checking = true;
        await this.loadUserData();
        this.showSnackbar({
          content: this.$t("checked"),
          color: "warning",
        });
      } catch (error) {
        this.handleError(error, "Error checking email verification");
      } finally {
        this.checking = false;
      }
    },
  },
  mounted() {
    this.sendVerificationEmail(true);
    this.loadUserDataInterval = setInterval(() => {
      if (this.emailVerified) {
        clearInterval(this.loadUserDataInterval);
      } else {
        this.loadUserData();
      }
    }, 5000);
  },
  beforeDestroy() {
    clearInterval(this.loadUserDataInterval);
  },
};
</script>
