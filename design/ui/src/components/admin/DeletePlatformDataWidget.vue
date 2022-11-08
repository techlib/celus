<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml">
en:
  dialog_text1: |
    You are about to delete all usage data for platform "<strong>{platform}</strong>".
    All the harvested and/or manually uploaded usage data will be removed. If you have
    SUSHI credentials present, they will be preserved to allow you subsequent reharvesting of the data.
    Also any harvests planned for the future will be preserved and run at their assigned time.
  dialog_text2: |
    This action cannot be undone. Data will be irreversibly lost.
  dialog_text3: |
    If you wish to proceed, please confirm the action by checking the checkbox bellow and pressing
    the 'Delete' button.
  confirmation: I confirm that I want to delete all usage data from platform "<strong>{platform}</strong>".
  in_progress: The delete process is in progress. It can take quite some time, please be patient.
  task_pending: Waiting for start of the delete process
  task_running: Delete in progress
  task_finished: The delete process has finished.
  all_organizations_selected: |
    You are deleting data for <strong>ALL ORGANIZATIONS</strong>. Please make sure this is what you
    really want.
cs:
  dialog_text1: |
    Chystáte se smazat veškerá data o využívanosti platformy "<strong>{platform}</strong>".
    Všechna stažená a/nebo ručně nahraná data budou smazána. Pokud máte pro platformu
    uloženy přihlašovací údaje pro SUSHI, budou zachována pro případné následné stažení nových dat.
    Také sklízení dat naplánované do budoucnosti bude zachováno a spouštěno ve stanoveném čase.
  dialog_text2: |
    Tuto akci není možné vzít zpět. Data budou nenávratně ztracena.
  dialog_text3: |
    Pokud si přejete pokračovat, potvrďte prosím tuto akci zaškrtnutím následujícího políčka a stisknutím
    tlačítka 'Smazat'.
  confirmation: Potvrzuji smazání všech dat o využívanosti pro platformu "<strong>{platform}</strong>".
  in_progress: Proces mazání je v běhu. Může to trvat déle, prosím o trpělivost.
  task_pending: Čekáme na spuštění procesu mazání
  task_running: Probíhá mazání
  task_finished: Proces mazání byl dokončen.
  all_organizations_selected: |
    Chystáte se smazat data pro <strong>VŠECHNY ORGANIZACE</strong>. Prosím ujistěte se, že to je
    opravdu to, co chcete udělat.
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
          <p v-html="$t('dialog_text3')"></p>
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
            {{ $t("dialog_text2") }}
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
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    async performDelete() {
      try {
        this.deletingId = this.platform.pk;
        let resp = await axios.post(
          `/api/organization/${this.selectedOrganizationId}/platform/${this.platform.pk}/delete-all-data/`
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
          this.$emit("finished", { platformId: this.platform.pk });
        } else {
          setTimeout(this.checkProgress, this.retryInterval);
        }
      }
    },
  },

  watch: {
    showDialog() {
      // do not remember the confirmation after cancel
      this.confirmed = false;
      // we are deleting, but the platform has changed
      if (this.deletingId && this.deletingId !== this.platform.pk) {
        this.task = null;
        this.deletingId = null;
      }
    },
  },
};
</script>
