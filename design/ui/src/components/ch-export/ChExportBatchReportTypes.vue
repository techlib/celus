<i18n lang="yaml">
en:
  report_types: Report tables from last sync
  reports_are_clickable: |
    Clickhouse offers a simple web interface to explore the database. Clicking on the report names above will take you
    to this interface with the structure of the table displayed.
    You can use the same interface to run queries on your data. This is convenient for testing and data exploration.
  progress_error: Failed to load progress
  tooltip_running: "Export in progress: {percentage}% complete{eta}"
  tooltip_completed: Export completed successfully. Click to open the table in Clickhouse.
  tooltip_pending: Export is waiting to start
  tooltip_failed: Export failed
  eta: ETA

cs:
  report_types: Tabulky reportů z poslední synchronizace
  reports_are_clickable: |
    Clickhouse nabízí jednoduché webové rozhraní pro exploraci databáze. Kliknutí na názvy reportů výše otevře toto
    rozhraní se zobrazením struktury tabulky.
    Stejné rozhraní můžete použít ke spuštění dotazů na vašich datech. To je vhodné pro testování a prohlížení dat.
  progress_error: Nepodařilo se načíst průběh
  tooltip_running: "Export probíhá: {percentage}% dokončeno{eta}"
  tooltip_completed: Export úspěšně dokončen. Kliknutím otevřete tabulku v Clickhouse.
  tooltip_pending: Export čeká na spuštění
  tooltip_failed: Export selhal
  eta: Odhadovaný čas
</i18n>

<template>
  <section v-if="batchProgress">
    <h3 class="text-h6 mt-8 mb-4">
      <v-icon class="me-2" color="grey" size="x-small">fa fa-table</v-icon>
      {{ $t("report_types") }}
      <v-tooltip location="bottom">
        <template #activator="{ props }">
          <v-chip
            class="text-subtitle-2 ms-4"
            variant="text"
            size="small"
            label
            color="grey-darken-1"
            v-bind="props"
            prepend-icon="far fa-clock"
          >
            <span>{{ createdRelative }}</span>
          </v-chip>
        </template>
        <span v-html="isoDateTimeFormat(batchProgress.created)"> </span>
      </v-tooltip>
    </h3>
    <div>
      <template v-for="task in sortedTasks" :key="task.id">
        <template v-if="task.status === 'running'">
          <!-- Chip with circular progress for running tasks -->
          <v-tooltip location="bottom">
            <template #activator="{ props }">
              <v-chip color="info" class="me-1 mb-1" v-bind="props">
                <template #prepend>
                  <v-progress-circular
                    :model-value="
                      (task.progress_current / task.progress_total) * 100 || 0
                    "
                    :size="20"
                    :width="2"
                    color="blue-darken-3"
                    class="me-2"
                  >
                  </v-progress-circular>
                </template>
                <template #default>{{ task.report_type }}</template>
              </v-chip>
            </template>
            <span>
              {{
                $t("tooltip_running", {
                  percentage: Math.round(
                    (task.progress_current / task.progress_total) * 100 || 0,
                  ),
                  eta: task.eta ? `, ${$t("eta")}: ${task.eta})` : "",
                })
              }}
            </span>
          </v-tooltip>
        </template>
        <template v-else-if="task.status === 'completed'">
          <!-- Chip for completed reports -->
          <v-tooltip location="bottom">
            <template #activator="{ props }">
              <v-chip
                :href="describeTableUrl(task.report_type)"
                target="_blank"
                color="primary"
                class="me-1 mb-1"
                v-bind="props"
              >
                <v-icon start size="x-small">fa fa-check</v-icon>
                {{ task.report_type }}
              </v-chip>
            </template>
            <span>{{ $t("tooltip_completed") }}</span>
          </v-tooltip>
        </template>
        <template v-else-if="task.status === 'pending'">
          <!-- Chip for pending reports -->
          <v-tooltip location="bottom">
            <template #activator="{ props }">
              <v-chip color="grey" class="me-1 mb-1" label v-bind="props">
                <v-icon start size="x-small">fa fa-hourglass-half</v-icon>
                {{ task.report_type }}
              </v-chip>
            </template>
            <span>{{ $t("tooltip_pending") }}</span>
          </v-tooltip>
        </template>
        <template v-else-if="task.status === 'failed'">
          <!-- Chip for failed reports -->
          <v-tooltip location="bottom">
            <template #activator="{ props }">
              <v-chip color="error" class="me-1 mb-1" label v-bind="props">
                <v-icon start size="x-small">fa fa-exclamation-triangle</v-icon>
                {{ task.report_type }}
              </v-chip>
            </template>
            <span>{{ $t("tooltip_failed") }}</span>
          </v-tooltip>
        </template>
        <template v-else>
          <!-- Default chip when status is unknown -->
          <v-chip
            :href="describeTableUrl(task.report_type)"
            target="_blank"
            class="me-1 mb-1"
            label
          >
            {{ task.report_type }}
          </v-chip>
        </template>
      </template>
    </div>
    <div class="mt-4 text-medium-emphasis">
      <v-icon class="me-1 mb-2" color="grey" size="x-small"
        >fa fa-info-circle</v-icon
      >
      {{ $t("reports_are_clickable") }}
    </div>
  </section>
</template>

<script>
import { isoDateTimeFormat } from "@/libs/dates";
import cancellation from "@/mixins/cancellation";
import { intlFormatDistance } from "date-fns";
import { mapGetters } from "vuex";

export default {
  name: "ChExportBatchReportTypes",
  emits: ["batch-finished"],
  mixins: [cancellation],
  props: {
    batchId: {
      type: Number,
      required: true,
    },
    chDatabase: {
      type: String,
      required: true,
    },
    chPassword: {
      type: String,
      required: true,
    },
  },
  data() {
    return {
      batchProgress: null,
      progressPollingInterval: null,
      progressError: null,
    };
  },
  computed: {
    ...mapGetters({
      clickhouseExportHost: "clickhouseExportHost",
      dateFnOptions: "dateFnOptions",
    }),
    sortedTasks() {
      if (!this.batchProgress || !this.batchProgress.tasks) {
        return [];
      }
      // Sort tasks by report_type name
      return [...this.batchProgress.tasks].sort((a, b) =>
        a.report_type.localeCompare(b.report_type),
      );
    },
    isRunning() {
      return this.batchProgress?.status === "running";
    },
    createdRelative() {
      return intlFormatDistance(this.batchProgress.created, new Date(), {
        addSuffix: true,
        includeSeconds: true,
        ...this.dateFnOptions,
      });
    },
  },
  methods: {
    isoDateTimeFormat,
    describeTableUrl(table) {
      let query = `DESCRIBE TABLE ${table};`;
      let base64Query = btoa(query);
      let url =
        `https://${this.clickhouseExportHost}:8443/play?user=${this.chDatabase}` +
        `&password=${this.chPassword}&run=1` +
        `&url=https%3A%2F%2F${this.clickhouseExportHost}%3A8443%2F%3Fdatabase%3D${this.chDatabase}` +
        `#${base64Query}`;
      return url;
    },
    async fetchBatchProgress() {
      if (!this.batchId) {
        return;
      }
      this.progressError = null;
      const { response, error } = await this.http({
        url: `/api/ch-export/batches/${this.batchId}/progress/`,
        dontShowError: true,
      });
      if (error) {
        this.progressError =
          error.response?.data?.detail || this.$t("progress_error");
        // Stop polling on error to avoid spamming
        this.stopProgressPolling();
      } else if (response) {
        const previousStatus = this.batchProgress?.status;
        this.batchProgress = response.data;
        // Stop polling if batch is no longer running
        if (
          this.batchProgress.status !== "running" &&
          this.progressPollingInterval
        ) {
          this.stopProgressPolling();
          // Emit event when batch finishes (status changes from running to something else)
          if (
            previousStatus === "running" &&
            this.batchProgress.status !== "running"
          ) {
            this.$emit("batch-finished");
          }
        }
      }
    },
    startProgressPolling() {
      if (!this.batchId) {
        return;
      }
      // Clear any existing interval
      this.stopProgressPolling();
      // Fetch immediately to check status
      this.fetchBatchProgress();
      // Only poll if batch is running
      if (this.isRunning) {
        // Then poll every 3 seconds
        this.progressPollingInterval = setInterval(() => {
          this.fetchBatchProgress();
        }, 3000);
      }
    },
    stopProgressPolling() {
      if (this.progressPollingInterval) {
        clearInterval(this.progressPollingInterval);
        this.progressPollingInterval = null;
      }
    },
  },
  watch: {
    batchId: {
      handler(newBatchId, oldBatchId) {
        if (newBatchId !== oldBatchId) {
          // Batch changed, reset progress and restart polling
          this.batchProgress = null;
          this.progressError = null;
          this.startProgressPolling();
        }
      },
      immediate: true,
    },
    "batchProgress.status": {
      handler(newStatus) {
        if (newStatus === "running") {
          // Start polling if not already polling
          if (!this.progressPollingInterval) {
            this.progressPollingInterval = setInterval(() => {
              this.fetchBatchProgress();
            }, 3000);
          }
        } else {
          // Stop polling if batch is no longer running
          this.stopProgressPolling();
        }
      },
    },
  },
  mounted() {
    // Fetch progress if batch exists
    if (this.batchId) {
      this.startProgressPolling();
    }
  },
  beforeUnmount() {
    this.stopProgressPolling();
  },
};
</script>
