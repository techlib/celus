<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml">
en:
  dialog_text1: |
    You are about to delete all usage data for platform "<strong>{platform}</strong>".
    All the harvested and/or manually uploaded usage data will be removed.
  delete_credentials: I want to delete SUSHI credentials as well.
  delete_credentials_info: |
    If selected, all existing SUSHI credentials for this platform will be deleted as well. <br/>
    Otherwise they will be preserved to allow you subsequent reharvesting of the data.
    Also any harvests planned for the future will be preserved and run at their assigned time.
  delete_platform: I want to delete the entire platform including all related data.
  delete_platform_info: |
    This is a custom platform, so it can be deleted. Otherwise it will be preserved and you can use it again in the future.
  platform_deletes_sushi: |
    When platform is deleted, all SUSHI credentials for it will automatically be deleted as well.
  delete_text: |
    This action cannot be undone. Data will be irreversibly lost.
  dialog_text3: |
    If you wish to proceed, please confirm the action by checking the checkbox bellow and pressing
    the 'Delete' button.
  confirmation: I confirm that I want to delete all the above mentioned data for platform "<strong>{platform}</strong>".
  in_progress: The delete process is in progress. It can take quite some time, please be patient.
  task_pending: Waiting for start of the delete process
  task_running: Delete in progress
  task_finished: The delete process has finished.
  all_organizations_selected: |
    You are deleting data for <strong>ALL ORGANIZATIONS</strong>. Please make sure this is what you
    really want.
  chunk_platform: the platform itself
  chunk_credentials: all SUSHI credentials for the platform
  chunk_data: all usage data for the platform
  what_will_be_deleted: What will be deleted
  what_will_be_preserved: What will be preserved
cs:
  dialog_text1: |
    Chystáte se smazat veškerá data o využívanosti platformy "<strong>{platform}</strong>".
    Všechna stažená a/nebo ručně nahraná data budou smazána.
  delete_credentials: Smazat také SUSHI přístupové údaje.
  delete_credentials_info: |
    Pokud je zaškrtnuto, všechny existující SUSHI přístupové údaje pro tuto platformu budou smazány
    spolu s daty. <br/>
    Jinak budou zachovány a budete moci je znovu použít pro stažení dat. Zachovávy budou také naplánovaná budoucí stažení dat.
  delete_platform: Smazat celou platformu včetně všech souvisejících dat.
  delete_platform_info: |
    Toto je vlastní platforma, takže může být smazána. Jinak bude zachována a budete moci ji znovu použít v budoucnu.
  platform_deletes_sushi: |
    Pokud je smazána platforma, budou smazány také všechny SUSHI přístupové údaje pro ni.
  delete_text: |
    Tuto akci není možné vzít zpět. Data budou nenávratně ztracena.
  dialog_text3: |
    Pokud si přejete pokračovat, potvrďte prosím tuto akci zaškrtnutím následujícího políčka a stisknutím
    tlačítka 'Smazat'.
  confirmation: Potvrzuji smazání všech výše uvedených dat pro platformu "<strong>{platform}</strong>".
  in_progress: Proces mazání je v běhu. Může to trvat déle, prosím o trpělivost.
  task_pending: Čekáme na spuštění procesu mazání
  task_running: Probíhá mazání
  task_finished: Proces mazání byl dokončen.
  all_organizations_selected: |
    Chystáte se smazat data pro <strong>VŠECHNY ORGANIZACE</strong>. Prosím ujistěte se, že to je
    opravdu to, co chcete udělat.
  chunk_platform: samotná platforma
  chunk_credentials: všechny SUSHI přístupové údaje pro platformu
  chunk_data: všechna data o využívanosti pro platformu
  what_will_be_deleted: Co bude smazáno
  what_will_be_preserved: Co bude zachováno
</i18n>

<template>
  <span>
    <v-btn color="error" @click="showDialog = true">
      <v-icon small class="pr-1">fa fa-trash</v-icon>
      {{ $t("labels.delete_all_platform_data") }}
    </v-btn>
    <v-dialog v-model="showDialog" max-width="800px">
      <v-card>
        <v-card-title>
          {{ $t("labels.delete_all_platform_data") }}
        </v-card-title>

        <v-card-text class="pt-4" v-if="task === null">
          <p v-html="$t('dialog_text1', { platform: platform.name })"></p>

          <div
            :class="isCustomPlatform && organizationSelected ? 'pb-2' : 'pb-6'"
          >
            <v-tooltip bottom max-width="640px">
              <template #activator="{ on }">
                <span v-on="on">
                  <v-checkbox
                    v-model="deleteCredentials"
                    dense
                    hide-details
                    :disabled="deletePlatform"
                  >
                    <template #label="">
                      <span v-html="$t('delete_credentials')"></span>
                    </template>
                  </v-checkbox>
                </span>
              </template>
              <div
                v-html="
                  deletePlatform
                    ? $t('platform_deletes_sushi')
                    : $t('delete_credentials_info')
                "
              ></div>
            </v-tooltip>
          </div>

          <div class="pb-6" v-if="isCustomPlatform && organizationSelected">
            <v-tooltip bottom max-width="640px">
              <template #activator="{ on }">
                <span v-on="on">
                  <v-checkbox
                    v-model="deletePlatform"
                    dense
                    hide-details
                    class="mt-0"
                  >
                    <template #label="">
                      <span v-html="$t('delete_platform')"></span>
                    </template>
                  </v-checkbox>
                </span>
              </template>
              <div v-html="$t('delete_platform_info')"></div>
            </v-tooltip>
          </div>

          <p v-html="$t('dialog_text3')"></p>

          <div class="d-flex px-4 align-stretch" style="min-height: 9rem">
            <v-col class="text-caption pt-4 ps-0 error--text">
              <v-card class="fill-height">
                <v-card-text class="text-caption error--text">
                  <strong>{{ $t("what_will_be_deleted") }}</strong
                  >:
                  <ul>
                    <v-fade-transition
                      v-for="chunk in deletedChunks"
                      :key="chunk"
                    >
                      <li>{{ $t(chunk) }}</li>
                    </v-fade-transition>
                  </ul>
                </v-card-text>
              </v-card>
            </v-col>

            <v-col class="text-caption pt-4 success--text">
              <v-card class="fill-height">
                <v-card-text class="text-caption success--text">
                  <strong>{{ $t("what_will_be_preserved") }}</strong
                  >: <span v-if="preservedChunks.length === 0">-</span>
                  <ul>
                    <v-fade-transition
                      v-for="chunk in preservedChunks"
                      :key="chunk"
                    >
                      <li>
                        {{ $t(chunk) }}
                      </li>
                    </v-fade-transition>
                  </ul>
                </v-card-text>
              </v-card>
            </v-col>
          </div>

          <div>
            <v-checkbox v-model="confirmed">
              <template #label="">
                <span
                  v-html="$t('confirmation', { platform: platform.name })"
                ></span>
              </template>
            </v-checkbox>
          </div>
          <v-alert :type="confirmed ? 'error' : 'warning'" outlined>
            <span v-html="$t('delete_text')"></span>
          </v-alert>
          <v-alert
            v-if="!organizationSelected"
            :type="confirmed ? 'error' : 'warning'"
          >
            <span v-html="$t('all_organizations_selected')"></span>
          </v-alert>
        </v-card-text>

        <v-card-text v-else>
          <div v-if="task.isFinished">
            <p v-html="$t('task_finished')"></p>
          </div>
          <div v-else>
            <p v-html="$t('in_progress')"></p>
            <v-progress-linear
              :indeterminate="task.progressPercentage === null"
              :value="task.progressPercentage"
              height="32px"
              >{{ progressText }}</v-progress-linear
            >
          </div>
        </v-card-text>

        <v-card-actions v-if="task === null" class="pb-4 mx-2">
          <v-spacer />
          <v-btn @click="showDialog = false">{{ $t("actions.cancel") }}</v-btn>
          <v-btn
            @click="performDelete()"
            :disabled="!confirmed"
            color="error"
            >{{ $t("actions.delete") }}</v-btn
          >
        </v-card-actions>
        <v-card-actions v-else class="pb-4 mx-2">
          <v-spacer />
          <v-btn @click="showDialog = false">{{ $t("actions.close") }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </span>
</template>
<script>
import ServerTask from "@/libs/server-task";
import axios from "axios";
import { mapActions, mapGetters, mapState } from "vuex";

export default {
  name: "DeletePlatformDataWidget",
  props: {
    platform: { required: true, type: Object },
  },

  data() {
    return {
      showDialog: false,
      task: null,
      confirmed: false,
      retryInterval: 2000,
      deletingId: null,
      deletePlatform: false,
      deleteCredentials: false,
      // used to remember the value when we automatically change it
      originalDeleteCredentials: false,
    };
  },

  computed: {
    ...mapState({
      selectedOrganizationId: "selectedOrganizationId",
    }),
    ...mapGetters({
      organizationSelected: "organizationSelected",
    }),
    progressText() {
      if (this.task === null) {
        return "";
      } else if (this.task.isRunning) {
        return this.$t("task_running");
      } else if (this.task.isFinished) {
        return this.$t("task_finished");
      }
      return this.$t("task_pending");
    },
    isCustomPlatform() {
      if (this.platform?.source?.organization) {
        return true;
      }
      return false;
    },
    deletedChunks() {
      let chunks = ["chunk_data"];
      if (this.deleteCredentials || this.deletePlatform) {
        chunks.push("chunk_credentials");
      }
      if (this.deletePlatform) {
        chunks.push("chunk_platform");
      }
      return chunks;
    },
    preservedChunks() {
      return ["chunk_credentials", "chunk_platform"].filter(
        (chunk) => !this.deletedChunks.includes(chunk)
      );
    },
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    async performDelete() {
      try {
        this.deletingId = this.platform.pk;
        let resp = await axios.post(
          `/api/organization/${this.selectedOrganizationId}/platform/${this.platform.pk}/delete-all-data/`,
          {
            delete_platform: this.deletePlatform,
            delete_credentials: this.deleteCredentials,
          }
        );
        this.task = new ServerTask(resp.data.task_id);
        this.checkProgress();
      } catch (error) {
        this.showSnackbar({
          content: "Error when initializing data delete " + error,
          color: "error",
        });
      }
    },
    async checkProgress() {
      if (this.task) {
        await this.task.getStatus();
        if (this.task.isFinished) {
          this.$emit("finished", {
            platformId: this.platform.pk,
            platformDeleted: this.deletePlatform,
          });
        } else {
          setTimeout(this.checkProgress, this.retryInterval);
        }
      }
    },
  },

  watch: {
    deletePlatform() {
      if (this.deletePlatform) {
        this.originalDeleteCredentials = this.deleteCredentials;
        // deleting the platform also deletes the credentials
        this.deleteCredentials = true;
      } else {
        this.deleteCredentials = this.originalDeleteCredentials;
      }
    },
    showDialog() {
      // do not remember the confirmation after cancel
      this.confirmed = false;
      this.deletePlatform = false;
      // we are deleting, but the platform has changed
      if (this.deletingId && this.deletingId !== this.platform.pk) {
        this.task = null;
        this.deletingId = null;
      }
    },
  },
};
</script>
