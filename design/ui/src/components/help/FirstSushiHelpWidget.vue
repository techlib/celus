<i18n lang="yaml">
en:
  add_credentials: Add credentials
  continue: Continue
cs:
  add_credentials: Přidat pověření
  continue: Dále
</i18n>
<i18n lang="yaml">
en:
  step1: Hello
  step1_text:
    Hello, it looks like you are new to Celus and there are no data in your account.
    Let me help you with setting up your first SUSHI download - it will give you some data
    to play with and at the same time teach you how Celus works.
  step2: SUSHI intro
  step2_text: |
    Celus works by obtaining usage statistics data from your vendor's server using
    the so called SUSHI protocol. In order to get the data, you have to know the address
    of the server and a few identification information, like the <strong>requestor ID</strong> and <strong>customer ID</strong>.
  step2_text_2: You can only obtain this information from your vendor.
  step2_text_3:
    This is what the dialog to enter SUSHI credentials looks like in Celus, to give you
    an idea of what you need to have ready.
  step3: Extras
  step3_text:
    Sometimes the provider will give you more credentials than the simple pair of
    requestor and customer ID. In COUNTER 5 it is often the <strong>API key</strong>, in
    COUNTER 4 it may be the username and password for HTTP authentication. If you get this
    information from your provider, do not panic - you will find Celus ready for this
    and you will be able to fill it in when registering your SUSHI credentials.
  step3_text_2: |
    <em>Note</em>: Please note that in some cases providers limit the access to
    their SUSHI servers to specific IP addresses. If you find that you are not able to
    download data even though your credentials are OK, it might be necessary to register
    the IP addresses of Celus.one with your provider. These are:
    <ul><li>142.93.169.41</li><li>2a03:b0c0:3:e0::465:c001 (for IPv6)</li></ul>
  step4: Test your credentials
  step4_text:
    After you put your credentials into Celus, we strongly advise to test them
    immediately. You can do so by clicking the
    <strong>Save & test harvesting</strong>
    button in the SUSHI credentials edit dialog. Then select one month in the near past
    and try to download the data. You will get a progress-bar for each download and
    very quickly receive a reply from the server. If there is any problem, please get back
    to the dialog and recheck your data.
  step5: Enable automatic harvesting
  step5_text: |
    When you have tested that your credentials work, we recommend activating automated
    harvesting of data using the <strong>Automatic harvesting</strong> toggle. For such credentials,
    Celus will automatically harvest data including past usage.
  step5_text_2: |
    <em>Note</em>: Please note that Celus does not start harvesting data immediately, but
    rather schedules periodic downloads for night hours when the traffic is lowest. Give it
    a day or two to fetch all your data.
  step6: Let's do it
  step6_text:
    OK, you should now know everything that is needed to get you started. Click the
    button below and add your first SUSHI credentials. Good luck ;)
</i18n>
<template>
  <v-stepper v-model="step" non-linear>
    <v-stepper-header>
      <v-stepper-step
        :step="1"
        :complete="step > 1"
        editable
        edit-icon="fa-check fa-small"
      >
        {{ $t("step1") }}
      </v-stepper-step>
      <v-stepper-step
        :step="2"
        :complete="step > 2"
        editable
        edit-icon="fa-check fa-small"
      >
        {{ $t("step2") }}
      </v-stepper-step>
      <v-stepper-step
        :step="3"
        :complete="step > 3"
        editable
        edit-icon="fa-check fa-small"
      >
        {{ $t("step3") }}
      </v-stepper-step>
      <v-stepper-step
        :step="4"
        :complete="step > 4"
        editable
        edit-icon="fa-check fa-small"
      >
        {{ $t("step4") }}
      </v-stepper-step>
      <v-stepper-step
        :step="5"
        :complete="step > 5"
        editable
        edit-icon="fa-check fa-small"
      >
        {{ $t("step5") }}
      </v-stepper-step>
      <v-stepper-step
        :step="6"
        :complete="step > 6"
        editable
        edit-icon="fa-check fa-small"
      >
        {{ $t("step6") }}
      </v-stepper-step>
    </v-stepper-header>

    <v-stepper-items>
      <v-stepper-content :step="1">
        <p>{{ $t("step1_text") }}</p>
        <p class="text-right">
          <v-btn @click="step++">{{ $t("continue") }}</v-btn>
        </p>
      </v-stepper-content>

      <v-stepper-content :step="2">
        <p v-html="$t('step2_text')"></p>
        <p v-html="$t('step2_text_2')"></p>
        <p>
          <img
            src="../../assets/sushi_credentials.png"
            alt="SUSHI credentials dialog example"
            class="outlined mt-5"
          />
        </p>
        <p>
          <em>{{ $t("step2_text_3") }}</em>
        </p>
        <p class="text-right">
          <v-btn @click="step++">{{ $t("continue") }}</v-btn>
        </p>
      </v-stepper-content>

      <v-stepper-content :step="3">
        <p v-html="$t('step3_text')"></p>
        <p v-html="$t('step3_text_2')"></p>
        <p class="text-right">
          <v-btn @click="step++">{{ $t("continue") }}</v-btn>
        </p>
      </v-stepper-content>

      <v-stepper-content :step="4">
        <p v-html="$t('step4_text')"></p>
        <p>
          <img
            src="../../assets/sushi_credentials-test.png"
            alt="Buttons available in the SUSHI credentials dialog"
            class="outlined mt-5"
          />
        </p>
        <p class="text-right">
          <v-btn @click="step++">{{ $t("continue") }}</v-btn>
        </p>
      </v-stepper-content>

      <v-stepper-content :step="5">
        <p v-html="$t('step5_text')"></p>
        <p v-html="$t('step5_text_2')"></p>
        <p>
          <img
            src="../../assets/sushi_credentials-enable.png"
            alt="Buttons available in the SUSHI credentials dialog"
            class="outlined mt-5"
          />
        </p>
        <p class="text-right">
          <v-btn @click="step++">{{ $t("continue") }}</v-btn>
        </p>
      </v-stepper-content>

      <v-stepper-content :step="6">
        <p v-html="$t('step6_text')"></p>

        <v-dialog v-model="showCredentialsDialog">
          <SushiCredentialsEditDialog
            v-model="showCredentialsDialog"
            key="create"
          ></SushiCredentialsEditDialog>
        </v-dialog>

        <p class="text-center pt-5">
          <v-btn @click="showCredentialsDialog = true" color="primary">{{
            $t("add_credentials")
          }}</v-btn>
        </p>
      </v-stepper-content>
    </v-stepper-items>
  </v-stepper>
</template>

<script>
import SushiCredentialsEditDialog from "../sushi/SushiCredentialsEditDialog";
import { mapActions } from "vuex";
export default {
  name: "FirstSushiHelpWidget",
  components: { SushiCredentialsEditDialog },
  data() {
    return {
      step: 1,
      showCredentialsDialog: false,
    };
  },

  methods: {
    ...mapActions({
      loadSushiCredentialsCount: "loadSushiCredentialsCount",
    }),
  },

  watch: {
    showCredentialsDialog(value) {
      if (!value) {
        // the dialog is closed
        this.loadSushiCredentialsCount();
      }
    },
  },
};
</script>

<style scoped lang="scss">
img.outlined {
  border: solid 1px #bbbbbb;
  width: 60%;
}
</style>
