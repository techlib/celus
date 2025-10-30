<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml" src="@/locales/dialog.yaml"></i18n>
<i18n lang="yaml" src="@/locales/sushi.yaml"></i18n>

<template>
  <v-card>
    <v-card-title
      >{{ $t(`sushi.auto_off_on.${off ? "off" : "on"}.title`) }} ({{
        credentials_length
      }})</v-card-title
    >
    <v-card-text>
      {{ $t(`sushi.auto_off_on.${off ? "off" : "on"}.text`) }}
    </v-card-text>
    <v-card-actions class="pb-4">
      <v-spacer></v-spacer>
      <v-btn @click="closeDialog()" variant="elevated" color="defaultButton">{{
        $t("close")
      }}</v-btn>
      <v-btn
        @click="trigger"
        color="primary"
        variant="elevated"
        :loading="loading"
        :prepend-icon="off ? 'fa fa-stop' : 'fa fa-play'"
      >
        {{ $t(`sushi.auto_off_on.${off ? "off" : "on"}.button`) }}
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script>
import axios from "axios";
import { mapActions } from "vuex";

export default {
  name: "AutoHarvestOffOnWidget",

  components: {},

  emits: ["triggered", "close"],

  props: {
    credentials: {
      required: true,
      type: Array,
    },
    off: {
      required: true,
      type: Boolean,
    },
  },

  data() {
    return {
      loading: false,
    };
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    closeDialog() {
      this.$emit("close");
    },
    async trigger() {
      const credentials_ids = this.credentials.map((e) => e.pk);
      this.loading = true;
      try {
        let response = await axios.post(
          "/api/sushi-credentials/update-enabled/",
          {
            enabled: !this.off,
            credentials: credentials_ids,
          },
        );
        if (response.data.updated > 0) {
          this.$emit("triggered");
          this.showSnackbar({
            content: this.$t(
              `sushi.auto_off_on.${this.off ? "off" : "on"}.success`,
            ),
            color: "success",
          });
        }
        this.closeDialog();
      } catch (error) {
        this.showSnackbar({
          content: "Error updating automatic harvesting: " + error,
          color: "error",
        });
      } finally {
        this.loading = false;
      }
    },
  },

  computed: {
    credentials_length() {
      return this.credentials.length;
    },
  },
};
</script>
