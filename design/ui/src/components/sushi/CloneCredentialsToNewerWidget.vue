<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml" src="@/locales/dialog.yaml"></i18n>
<i18n lang="yaml" src="@/locales/sushi.yaml"></i18n>

<template>
  <v-card>
    <v-card-title>{{ $t("sushi.clone_to_newer.title") }}</v-card-title>
    <v-card-text>
      <v-alert type="info" variant="outlined" class="mt-2 mb-0">
        <p>{{ $t("sushi.clone_to_newer.alert_text_p1") }}</p>
        <p class="mb-0 mt-4">
          <i18n-t keypath="sushi.clone_to_newer.alert_text_p2">
            <template #link>
              <a
                href="https://support.celus.net/support/solutions/articles/103000331653"
                target="_blank"
                class="text-info active_link"
                >{{ $t("sushi.clone_to_newer.link_text") }}</a
              >
            </template>
          </i18n-t>
        </p>
      </v-alert>

      <div
        class="pt-6 text-disabled"
        v-html="$t('sushi.clone_to_newer.info', { count: credentialsCount })"
      ></div>

      <v-card elevation="0" outlined class="mt-6 mb-2">
        <v-card-subtitle class="pb-2 font-weight-light">{{
          $t("overview")
        }}</v-card-subtitle>
        <v-card-text>
          <table class="overview">
            <tr>
              <th class="text-disabled">
                {{ $t("sushi.update.can_update_verified_legend") }}
              </th>
              <td class="text-right text-disabled">{{ safeToCloneCount }}</td>
              <td class="pl-2">
                <v-icon v-if="safeToCloneCount" color="success" size="x-small"
                  >fa fa-check-circle</v-icon
                >
              </td>
            </tr>
            <tr>
              <th class="text-disabled">
                {{ $t("sushi.update.can_update_legend") }}
              </th>
              <td class="text-right text-disabled">{{ unsafeToCloneCount }}</td>
              <td class="pl-2">
                <v-icon v-if="unsafeToCloneCount" color="warning" size="x-small"
                  >fa fa-exclamation-triangle</v-icon
                >
              </td>
            </tr>
          </table>
        </v-card-text>
      </v-card>

      <div class="mt-8" v-if="unsafeToCloneCount">
        <v-checkbox
          v-model="iAmSure"
          :label="$t('sushi.update.i_am_sure')"
          color="orange"
        ></v-checkbox>
      </div>
    </v-card-text>
    <v-card-actions class="px-6 pb-4">
      <v-switch
        v-model="startHarvesting"
        :label="$t('actions.start_harvesting')"
        color="primary"
        hide-details
      ></v-switch>
      <v-spacer></v-spacer>
      <v-btn @click="closeDialog()" variant="elevated" color="defaultButton">{{
        $t("close")
      }}</v-btn>
      <v-btn
        @click="cloneToNewer()"
        color="primary"
        :loading="saving"
        :disabled="!!unsafeToCloneCount && !iAmSure"
        variant="elevated"
      >
        {{ $t("sushi.clone_to_newer.button") }}
      </v-btn>
    </v-card-actions>

    <v-dialog
      v-model="showHarvestDialog"
      max-width="1320px"
      content-class="top-dialog"
    >
      <v-card>
        <v-card-title>{{
          $t("sushi.update.harvest_new_credentials")
        }}</v-card-title>
        <v-card-text class="pb-0">
          <HarvestSelectedWidget
            v-if="showHarvestDialog"
            :credentials="newCredentials"
            :retry-interval="5000"
            :show-platform="true"
            :show-organization="true"
            :show-reharvest="false"
          >
          </HarvestSelectedWidget>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn
            @click="closeDialog()"
            class="mb-5 mr-5"
            variant="elevated"
            color="defaultButton"
            >{{ $t("close") }}</v-btn
          >
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card>
</template>

<script>
import axios from "axios";
import { mapActions } from "vuex";
import cancellation from "@/mixins/cancellation";
import HarvestSelectedWidget from "@/components/sushi/HarvestSelectedWidget.vue";

export default {
  name: "MarkCredentialsAsFixedWidget",

  components: { HarvestSelectedWidget },

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
      iAmSure: false,
      showHarvestDialog: false,
      newCredentials: [],
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
          inputData,
        );
        this.newCredentials = response.data;
        if (this.newCredentials.length) {
          // let the parent know that there are new credentials,
          // but he does not need to know which ones - he will fetch all anyway
          this.$emit("new-credentials");
          if (this.startHarvesting) {
            this.showHarvestDialog = true;
          }
        }
        this.showSnackbar({
          content: this.$t("sushi.clone_to_newer.success"),
          color: "success",
        });
        if (!this.showHarvestDialog) {
          this.closeDialog();
        }
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
    safeToCloneCount() {
      return this.credentials.filter(
        (item) => item.can_update && item.has_51_provider && !item.broken,
      ).length;
    },
    unsafeToCloneCount() {
      return this.credentials.filter(
        (item) => item.can_update && !item.has_51_provider && !item.broken,
      ).length;
    },
  },

  mounted() {},
};
</script>

<style lang="scss">
.info_text {
  color: rgba(0, 0, 0, 0.6);
}

.info_link {
  font-weight: 600;
}

.active_link {
  font-weight: 600;
}
</style>
