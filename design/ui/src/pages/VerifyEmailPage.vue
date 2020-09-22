<i18n>
en:
    no_such_key: Sorry, but we could not verify your email - the verification link is probably malformed
    some_error: 'Sorry, but we could not verify your email due to the following error: "{error}"'
    success: Your address was successfully verified
    go_to_celus: Continue to Celus

cs:
    no_such_key: Je nám to líto, ale nemohli jsme ověřit váš email - ověřovací odkaz je pravděpodobně poškozený
    some_error: 'Je nám to líto, ale nemohli jsme ověřit váš email z důvodu následující chyby: "{error}"'
    success: Vaše adresa byla úspěšně ověřena
    go_to_celus: Pokračujte do aplikace Celus
</i18n>

<template>
  <v-app>
    <v-container class="center">
      <v-row>
        <v-col>
          <img
            src="../assets/celus-plus-white-vertical-nobg.svg"
            height="158"
            alt="Celus Logo"
          />
        </v-col>
      </v-row>

      <v-row>
        <v-col v-if="!attemptFinished && key">
          Verifying your email <v-icon class="ml-4">fa-spinner fa-spin</v-icon>
        </v-col>
      </v-row>

      <v-row>
        <v-col>
          <v-alert v-if="!key" type="error">
            {{ $t("no_such_key") }}
          </v-alert>
          <v-alert v-else-if="error" type="error">
            {{ $t(error, { error: errorObj }) }}
          </v-alert>
          <v-alert v-else-if="emailVerified" type="success">
            <div v-html="$t('success')"></div>
            <div>
              <router-link :to="{ name: 'dashboard' }" class="continue">{{
                $t("go_to_celus")
              }}</router-link>
            </div>
          </v-alert>
        </v-col>
      </v-row>
    </v-container>
  </v-app>
</template>

<script>
import axios from "axios";

export default {
  name: "VerifyEmailPage",

  data() {
    return {
      key: this.$route.query.key,
      emailVerified: false,
      error: null,
      errorObj: null,
      attemptFinished: false,
    };
  },

  methods: {
    async verifyEmail() {
      try {
        await axios.post(
          `/api/rest-auth/registration/verify-email/`,
          { key: this.key },
          { privileged: true }
        );
        this.attemptFinished = true;
        this.emailVerified = true;
      } catch (error) {
        this.errorObj = error;
        if (error.response.status === 404 && "detail" in error.response.data) {
          this.error = "no_such_key";
        } else {
          this.error = "some_error";
        }
        this.attemptFinished = true;
      }
    },
  },

  mounted() {
    if (this.key) {
      this.verifyEmail();
    }
  },
};
</script>

<style scoped lang="scss">
.center {
  text-align: center;
}

a.continue {
  font-size: 125%;
  color: white;
  font-weight: 900;
}
</style>
