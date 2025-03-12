<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml" src="@/locales/dialog.yaml"></i18n>
<i18n lang="yaml" src="@/locales/sushi.yaml"></i18n>

<template>
  <v-card>
    <v-card-title
      >{{ $t("sushi.mark_as_fixed.title") }} ({{
        credentials_length
      }})</v-card-title
    >
    <v-card-text>
      {{ $t("sushi.mark_as_fixed.tooltip") }}
    </v-card-text>
    <v-card-actions class="pb-4">
      <v-spacer></v-spacer>
      <v-btn @click="closeDialog()" variant="elevated" color="defaultButton">{{
        $t("close")
      }}</v-btn>
      <v-btn
        @click="markCheckedFixed()"
        color="primary"
        variant="elevated"
        :loading="saving"
      >
        {{ $t("sushi.mark_as_fixed.button") }}
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script>
import axios from "axios";
import { mapActions } from "vuex";
import cancellation from "@/mixins/cancellation";

export default {
  name: "MarkCredentialsAsFixedWidget",

  components: {},

  mixins: [cancellation],

  props: {
    credentials: {
      required: true,
      type: Array,
    },
  },

  data() {
    return {
      saving: false,
    };
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    closeDialog() {
      this.$emit("close");
    },
    async markCheckedFixed() {
      const inputData = this.credentials.map((e) => {
        return { credentials_id: e.pk };
      });
      this.saving = true;
      try {
        let response = await axios.post(
          "/api/sushi-credentials/unset-broken/",
          inputData,
        );
        for (const credentials of response.data) {
          this.$emit("update-credentials", credentials);
        }
        this.showSnackbar({
          content: this.$t("sushi.mark_as_fixed.success"),
          color: "success",
        });
        this.closeDialog();
      } catch (error) {
        this.showSnackbar({
          content: "Error marking SUSHI credentials as fixed: " + error,
          color: "error",
        });
      } finally {
        this.saving = false;
      }
    },
  },

  computed: {
    credentials_length() {
      return this.credentials.length;
    },
  },

  mounted() {},
};
</script>

<style lang="scss"></style>
