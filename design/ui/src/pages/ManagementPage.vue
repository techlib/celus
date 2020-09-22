<i18n lang="yaml">
en:
  background_tasks: Background tasks
  background_tasks_info:
    Following tasks are run periodically in the background. Here you can trigger
    their immediate start. Because the tasks can wait in a queue or be temporarily blocked by
    other tasks, it is not possible to observe their progress in real time.
  erms_sync_organizations: Sync organizations with ERMS
  erms_sync_users_and_identities: Sync user accounts with ERMS
  erms_sync_platforms: Sync platforms with ERMS
  fetch_new_sushi_data: Check for new SUSHI data
  task_success: Task was successfully submitted
  task_error: An error occurred during task submission
  management_page: Management page
  django_admin: Django admin
  django_admin_text: You can use <a href="{adminUrl}" target="_blank">Django admin</a> for low-level management.

cs:
  background_tasks: Úlohy na pozadí
  background_tasks_info:
    Následující úlohy jsou systémem pravidelně automaticky spouštěny na pozadí. Zde
    je můžete spustit okamžitě. Vzhledem k tomu, že úlohy mohou být zařazeny do fronty a nebo
    blokovány jinými úlohami, není možné sledovat průběh úlohy v reálném čase.
  erms_sync_organizations: Synchronizace organizací s ERMS
  erms_sync_users_and_identities: Synchronizace uživatelských účtů s ERMS
  erms_sync_platforms: Synchronizace platforem s ERMS
  fetch_new_sushi_data: Spustit stahování nových dat přes SUSHI
  task_success: Úloha byla úspěšně zadána
  task_error: Při zadávání úlohy došlo k chybě
  management_page: Správa systému
  django_admin: Django admin
  django_admin_text: Pro nízkoúrovňový přístup ke správě systému můžete využít rozhraní <a href="{adminUrl}" target="_blank">Django admin</a>.
</i18n>

<template>
  <v-container>
    <!--h1 class="text-h3 mb-4">{{ $t('management_page') }}</h1-->

    <section v-if="user.is_superuser || user.is_staff">
      <h2 class="text-h4 mb-3">{{ $t("django_admin") }}</h2>

      <p
        v-html="$t('django_admin_text', { adminUrl: getCelusAdminSitePath })"
        v-bind:title="getCelusAdminSitePath"
        class="font-weight-light"
      ></p>
    </section>

    <h2 class="text-h4 mb-3">{{ $t("background_tasks") }}</h2>
    <p class="font-weight-light" v-text="$t('background_tasks_info')"></p>

    <v-alert
      v-if="lastTask"
      :type="lastTask.success ? 'success' : 'error'"
      dismissible
      elevation="1"
    >
      <h4 class="heading-2" v-text="lastTask.task.title"></h4>

      <div v-if="lastTask.success" v-text="$t('task_success')"></div>
      <div v-else>
        {{ $t("task_error") }}
        <div v-if="lastTask.error">
          <i>{{ lastTaks.error }}</i>
        </div>
      </div>
      <div class="font-weight-light" v-text="lastTask.time"></div>
    </v-alert>

    <table>
      <tr v-for="task in celeryTasks" :key="task.taskName">
        <th v-text="task.title" class="text-left pr-2 pb-3"></th>
        <td class="pb-3">
          <v-btn @click="runCeleryTask(task)" color="primary">
            <v-icon
              small
              class="fa-fw"
              v-text="task.icon ? task.icon : 'fas fa-sync-alt'"
            ></v-icon>
          </v-btn>
        </td>
      </tr>
    </table>
  </v-container>
</template>

<script>
import axios from "axios";
import { isoDateTimeFormat } from "@/libs/dates";
import { mapState, mapGetters } from "vuex";

export default {
  name: "ManagementPage",
  data() {
    return {
      lastTask: null,
      allCeleryTasks: [
        {
          title: this.$t("erms_sync_platforms"),
          taskName: "erms-sync-platforms",
          filter: (context) => context.uses_erms,
        },
        {
          title: this.$t("erms_sync_organizations"),
          taskName: "erms-sync-organizations",
          filter: (context) => context.uses_erms,
        },
        {
          title: this.$t("erms_sync_users_and_identities"),
          taskName: "erms-sync-users-and-identities",
          filter: (context) => context.uses_erms,
        },
        {
          title: this.$t("fetch_new_sushi_data"),
          taskName: "fetch-new-sushi-data",
          icon: "fas fa-running",
        },
      ],
    };
  },
  computed: {
    ...mapState({
      user: "user",
      basicInfo: "basicInfo",
    }),
    ...mapGetters({
      celusAdminSitePath: "celusAdminSitePath",
    }),
    getCelusAdminSitePath() {
      return `/${this.celusAdminSitePath}`;
    },
    celeryTasks() {
      let context = {
        uses_erms: !!this.basicInfo.USES_ERMS,
      };
      return this.allCeleryTasks.filter((item) =>
        item.filter ? item.filter(context) : true
      );
    },
  },
  methods: {
    async runCeleryTask(task) {
      this.lastTask = null;
      try {
        let result = await axios.post(`/api/run-task/${task.taskName}`, {});
        this.lastTask = {
          task: task,
          success: true,
          time: isoDateTimeFormat(new Date()),
        };
      } catch (error) {
        this.lastTask = {
          task: task,
          success: false,
          error: error,
          time: isoDateTimeFormat(new Date()),
        };
      }
    },
  },
};
</script>

<style scoped></style>
