<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml" src="@/locales/dialog.yaml"></i18n>
<i18n lang="yaml" src="@/locales/sushi.yaml"></i18n>

<template>
  <v-card>
    <v-card-title
      >{{ $t(`sushi.reports_from_platform.title`) }} ({{
        credentials_length
      }})</v-card-title
    >
    <v-card-text>
      {{ $t(`sushi.reports_from_platform.text`) }}
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
        prepend-icon="fa fa-cogs"
      >
        {{ $t(`sushi.reports_from_platform.button`) }}
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script>
import axios from "axios";
import { mapActions } from "vuex";

export default {
  name: "UseReportsFromPlatformDialog",

  components: {},

  emits: ["triggered", "close"],

  props: {
    credentials: {
      required: true,
      type: Array,
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
      const data = this.credentials.map((e) => {
        return { credentials_id: e.pk };
      });
      this.loading = true;
      try {
        let response = await axios.post(
          "/api/sushi-credentials/switch-to-platforms-report-types/",
          data,
        );
        if (response.data.updated > 0) {
          this.$emit("triggered");
          this.showSnackbar({
            content: this.$t("sushi.reports_from_platform.success"),
            color: "success",
          });
        }
        this.closeDialog();
      } catch (error) {
        this.showSnackbar({
          content:
            "Could not switch credentials to use counter reports from platform: " +
            +error,
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
