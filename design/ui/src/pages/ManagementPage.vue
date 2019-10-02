<i18n>
en:
    background_tasks: Background tasks
    background_tasks_info: Following tasks are run periodically in the background. Here you can trigger
       their immediate start. Because the tasks can wait in a queue or be temporarily blocked by
       other tasks, it is not possible to observe their progress in real time.
    erms_sync_organizations: Sync organizations with ERMS
    erms_sync_users_and_identities: Sync user accounts with ERMS
    task_success: Task was successfully submitted
    task_error: An error occurred during task submission

cs:
    background_tasks: Úlohy na pozadí
    background_tasks_info: Následující úlohy jsou systémem pravidelně automaticky spouštěny na pozadí. Zde
        je můžete spustit okamžitě. Vzhledem k tomu, že úlohy mohou být zařazeny do fronty a nebo
        blokovány jinými úlohami, není možné sledovat průběh úlohy v reálném čase.
    erms_sync_organizations: Synchronizace organizací s ERMS
    erms_sync_users_and_identities: Synchronizace uživatelských účetů s ERMS
    task_success: Úloha byla úspěšně zadána
    task_error: Při zadávání úlohy došlo k chybě
</i18n>

<template>
    <div>
        <h1 class="display-2 mb-4">
            Management page
        </h1>

        <v-alert
                v-if="lastTask"
                :type="lastTask.success ? 'success' : 'error'"
                dismissible
                elevation="1"

        >
            <h4 class="heading-2" v-text="lastTask.task.title"></h4>

            <div v-if="lastTask.success" v-text="$t('task_success')"></div>
            <div v-else>
                {{ $t('task_error') }}
                <div v-if="lastTask.error"><i>{{ lastTaks.error }}</i></div>
            </div>
            <div class="font-weight-light" v-text="lastTask.time"></div>
        </v-alert>

        <h2 class="display-1 mb-3">{{ $t('background_tasks') }}</h2>
        <p class="font-weight-light" v-text="$t('background_tasks_info')"></p>
        <table>
            <tr v-for="task in celeryTasks" :key="task.taskName">
                <th v-text="task.title" class="text-left pr-2"></th>
                <td>
                    <v-btn @click="runCeleryTask(task)" color="primary">
                        <v-icon small class="fa-fw" v-text="task.icon ? task.icon : 'fas fa-running'"></v-icon>
                    </v-btn>
                </td>
            </tr>

        </table>
    </div>
</template>

<script>
  import axios from 'axios'
  import {isoDateTimeFormat} from '../libs/dates'

  export default {
    name: "ManagementPage",
    data () {
      return {
        lastTask: null,
      }
    },
    computed: {
      celeryTasks () {
        return [
          {
            title: this.$t('erms_sync_organizations'),
            taskName: 'erms-sync-organizations',
            icon: 'fas fa-sync'
          },
           {
            title: this.$t('erms_sync_users_and_identities'),
            taskName: 'erms-sync-users-and-identities',
          },
        ]
      },
    },
    methods: {
      async runCeleryTask (task) {
        this.lastTask = null
        try {
          let result = await axios.post(`/api/run-task/${task.taskName}`, {})
          this.lastTask = {
            task: task,
            success: true,
            time: isoDateTimeFormat(new Date()),
          }
        } catch (error) {
          this.lastTask = {
            task: task,
            success: false,
            error: error,
            time: isoDateTimeFormat(new Date()),
          }
        }
      }
    }

  }
</script>

<style scoped>

</style>
