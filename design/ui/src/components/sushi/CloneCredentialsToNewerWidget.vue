<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml" src="@/locales/dialog.yaml"></i18n>
<i18n lang="yaml" src="@/locales/sushi.yaml"></i18n>

<template>
  <v-card>
    <v-card-title>{{ $t("sushi.clone_to_newer.title") }}</v-card-title>
    <v-card-text
      v-html="$t('sushi.clone_to_newer.info', { count: credentialsCount })"
    />
    <v-card-actions class="px-6 pb-4">
      <v-switch
        v-model="startHarvesting"
        :label="$t('actions.start_harvesting')"
      ></v-switch>
      <v-spacer></v-spacer>
      <v-btn @click="closeDialog()">{{ $t("close") }}</v-btn>
      <v-btn @click="cloneToNewer()" color="primary" :loading="saving">
        {{ $t("sushi.clone_to_newer.button") }}
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
      startHarvesting: true,
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
    async cloneToNewer() {
      const inputData = this.credentials.map((e) => {
        return { credentials_id: e.pk };
      });
      this.saving = true;
      try {
        let response = await axios.post(
          "/api/sushi-credentials/clone-to-newer/",
          inputData
        );
        let credentials = response.data;
        this.$emit(
          "new-credentials",
          credentials.map((e) => e.pk),
          this.startHarvesting
        );
        this.showSnackbar({
          content: this.$t("sushi.clone_to_newer.success"),
          color: "success",
        });
        this.closeDialog();
      } catch (error) {
        this.showSnackbar({
          content: "Error cloning SUSHI credentials: " + error,
          color: "error",
        });
      } finally {
        this.saving = false;
      }
    },
  },

  computed: {
    credentialsCount() {
      return this.credentials.length;
    },
  },

  mounted() {},
};
</script>

<style lang="scss"></style>
