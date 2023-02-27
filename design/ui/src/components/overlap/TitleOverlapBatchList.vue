<i18n src="@/locales/common.yaml" lang="yaml"></i18n>
<i18n lang="yaml">
en:
  matched_rows: Matched rows
  total_rows: Total rows
  delete_batch_tt: Delete this file from Celus
  delete_batch_text: Are you sure you want to delete this file?
  batch_deleted: File was successfully deleted.
  annotated_file_tt: Download annotated file
  source_file_tt: Download copy of the source file

cs:
  matched_rows: Nalezené řádky
  total_rows: Celkem řádků
  delete_batch_tt: Odstranit tento soubor z Celusu
  delete_batch_text: Opravdu chcete odstranit tento soubor?
  batch_deleted: Soubor byl úspěšně odstraněn.
  annotated_file_tt: Stáhnout anotovaný soubor
  source_file_tt: Stáhnout kopii zdrojového souboru
</i18n>

<template>
  <div>
    <v-data-table
      :items="batches"
      :loading="loading"
      item-key="pk"
      :headers="headers"
      sort-by="created"
      sort-desc
    >
      <template #top>
        <v-btn color="primary" @click="showUploadDialog = true">
          <v-icon small class="me-2">fa-upload</v-icon>
          {{ $t("actions.upload_file_for_annotation") }}
        </v-btn>
      </template>

      <template #item.created="{ item }">
        <v-tooltip bottom>
          <template #activator="{ on }">
            <span v-on="on">{{ relativeDate(item.created) }}</span>
          </template>
          <span>{{ isoDateTimeFormat(item.created) }}</span>
        </v-tooltip>
      </template>

      <template #item.state="{ item }">
        <!-- processing -->
        <ServerTaskMonitor
          v-if="item.state === 'processing' && item.task"
          :value="item.task"
          dense
          @finished="refetchBatch(item.pk)"
        />
        <!-- failed -->
        <v-tooltip bottom v-else-if="item.state === 'failed'">
          <template #activator="{ on }">
            <span v-on="on">
              <v-icon color="error" small>fa-exclamation-circle</v-icon>
            </span>
          </template>
          <span>
            <span class="font-weight-bold">{{ $t("labels.error") }}:</span>
            {{ item.processing_info.error }}
          </span>
        </v-tooltip>
        <!-- other states -->
        <v-tooltip bottom v-else>
          <template #activator="{ on }">
            <v-icon :color="stateToColor(item.state)" small v-on="on">
              {{ stateToIcon(item.state) }}
            </v-icon>
          </template>
          {{ item.state }}
        </v-tooltip>
      </template>

      <template #item.source_file="{ item }">
        <v-tooltip bottom>
          <template #activator="{ on }">
            <a :href="item.source_file" target="_blank" v-on="on">
              <v-icon small>fa fa-file</v-icon>
            </a>
          </template>
          <span>{{ $t("source_file_tt") }}</span>
        </v-tooltip>
      </template>

      <template #item.annotated_file="{ item }">
        <v-tooltip bottom v-if="item.annotated_file">
          <template #activator="{ on }">
            <a :href="item.annotated_file" target="_blank" v-on="on">
              <v-icon
                small
                color="primary"
                :class="item.just_finished ? 'pulse' : ''"
                >fa fa-download</v-icon
              >
            </a>
          </template>
          <span>{{ $t("annotated_file_tt") }}</span>
        </v-tooltip>
        <span v-else>-</span>
      </template>

      <template #item.matched_rows="{ item }">
        <span
          v-if="
            item.processing_info.stats && item.processing_info.stats.row_count
          "
          >{{
            item.processing_info.stats.row_count -
            item.processing_info.stats.no_match
          }}
          /
          {{ item.processing_info.stats.row_count }}
        </span>
        <span v-else>-</span>
      </template>
      <template #item.actions="{ item }">
        <v-tooltip bottom>
          <template #activator="{ on }">
            <v-btn icon @click="deleteBatch(item.pk)" color="error" v-on="on">
              <v-icon small>fa fa-trash</v-icon>
            </v-btn>
          </template>
          <span>{{ $t("delete_batch_tt") }}</span>
        </v-tooltip>
      </template>
    </v-data-table>

    <TitleOverlapUploadFileDialog
      v-if="showUploadDialog"
      v-model="showUploadDialog"
      @upload-file="uploadFile"
    />
  </div>
</template>

<script>
import cancellation from "@/mixins/cancellation";
import { mapActions, mapGetters, mapState } from "vuex";
import {
  isoDateTimeFormat,
  isoDateTimeFormatSpans,
  parseDateTime,
} from "@/libs/dates";
import ServerTaskMonitor from "@/components/tasks/ServerTaskMonitor.vue";
import ServerTask from "@/libs/server-task";
import formatRelative from "date-fns/formatRelative";
import { formatDistance } from "date-fns";
import TitleOverlapUploadFileDialog from "@/components/overlap/TitleOverlapUploadFileDialog";

export default {
  name: "TitleOverlapBatchList",
  components: { TitleOverlapUploadFileDialog, ServerTaskMonitor },

  mixins: [cancellation],

  data() {
    return {
      batches: [],
      loading: false,
      showUploadDialog: false,
      dataFile: null,
      now: null,
      timer: null,
    };
  },

  computed: {
    ...mapState({
      selectedOrganizationId: "selectedOrganizationId",
    }),
    ...mapGetters({
      dateFnOptions: "dateFnOptions",
    }),
    headers() {
      return [
        { text: this.$t("labels.created"), value: "created" },
        { text: this.$t("labels.organization"), value: "organization.name" },
        { text: this.$t("labels.status"), value: "state" },
        {
          text: this.$t("matched_rows"),
          value: "matched_rows",
          sortable: false,
        },
        {
          text: this.$t("labels.source_file"),
          value: "source_file",
          sortable: false,
        },
        {
          text: this.$t("labels.annotated_file"),
          value: "annotated_file",
          sortable: false,
        },
        {
          text: this.$t("title_fields.actions"),
          value: "actions",
          sortable: false,
        },
      ];
    },
  },

  methods: {
    isoDateTimeFormat,
    formatRelative,
    ...mapActions({ showSnackbar: "showSnackbar" }),
    isoDateTimeFormatSpans,
    async fetchBatches() {
      this.loading = true;
      let result = await this.http({
        method: "get",
        url: "/api/title-overlap-batch/",
      });
      if (!result.error) {
        this.batches = result.response.data;
      }
      this.loading = false;
    },
    async uploadFile(file) {
      this.loading = true;
      let formData = new FormData();
      formData.append("source_file", file);
      if (this.selectedOrganizationId > 0) {
        formData.append("organization", this.selectedOrganizationId);
      }
      let result = await this.http({
        method: "post",
        url: "/api/title-overlap-batch/",
        data: formData,
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });
      if (!result.error) {
        this.showUploadDialog = false;
        await this.fetchBatches();
        this.processBatch(result.response.data.pk);
      }
      this.loading = false;
    },
    async processBatch(pk) {
      let result = await this.http({
        method: "post",
        url: `/api/title-overlap-batch/${pk}/process/`,
      });
      if (!result.error) {
        const serverBatch = result.response?.data?.batch;
        const taskId = result.response?.data?.task_id;
        if (serverBatch) {
          let matchingBatch = this.batches.find((b) => b.pk === pk);
          if (matchingBatch) {
            matchingBatch.state = serverBatch.state;
            if (taskId)
              matchingBatch.task = new ServerTask(result.response.data.task_id);
          }
        }
      }
    },
    async refetchBatch(pk) {
      let result = await this.http({
        method: "get",
        url: `/api/title-overlap-batch/${pk}/`,
      });
      if (!result.error) {
        const serverBatch = result.response?.data;
        let matchingBatch = this.batches.find((b) => b.pk === pk);
        if (matchingBatch) {
          matchingBatch.state = serverBatch.state;
          matchingBatch.processing_info = serverBatch.processing_info;
          matchingBatch.annotated_file = serverBatch.annotated_file;
          matchingBatch.last_updated = serverBatch.last_updated;
          matchingBatch.just_finished = true;
        }
      }
    },
    async deleteBatch(pk) {
      const goOn = await this.$confirm(this.$t("delete_batch_text"), {
        title: this.$t("confirm_delete"),
        buttonTrueText: this.$t("actions.delete"),
        buttonFalseText: this.$t("actions.cancel"),
      });
      if (goOn) {
        await this.deleteBatchConfirmed(pk);
      }
    },
    async deleteBatchConfirmed(pk) {
      this.loading = true;
      let result = await this.http({
        method: "delete",
        url: `/api/title-overlap-batch/${pk}/`,
      });
      if (!result.error) {
        this.showSnackbar({
          content: this.$t("batch_deleted"),
          color: "success",
        });
        await this.fetchBatches();
      }
      this.loading = false;
    },
    stateToColor(state) {
      switch (state) {
        case "processing":
          return "blue";
        case "done":
          return "green";
        case "failed":
          return "red";
        default:
          return "grey";
      }
    },
    stateToIcon(state) {
      switch (state) {
        case "processing":
          return "fa-clock";
        case "done":
          return "fa-check-circle";
        case "failed":
          return "fa-exclamation-circle";
        default:
          return "fa-question-circle";
      }
    },
    relativeDate(date) {
      return formatDistance(parseDateTime(date), this.now, {
        addSuffix: true,
        includeSeconds: true,
        ...this.dateFnOptions,
      });
    },
    updateNow() {
      this.now = new Date();
    },
  },

  mounted() {
    this.fetchBatches();
    // set up timer to periodically update the relative dates
    let that = this;
    function update() {
      that.updateNow();
      that.timer = setTimeout(update, 10000);
    }
    update();
  },

  beforeDestroy() {
    clearTimeout(this.timer);
  },
};
</script>

<style scoped lang="scss">
.pulse {
  animation: pulse-animation 750ms 20;
}

@keyframes pulse-animation {
  0% {
    box-shadow: 0 0 0 0px rgba(0, 160, 100, 0.3);
    background-color: rgba(0, 160, 100, 0.3);
  }
  100% {
    box-shadow: 0 0 0 30px rgba(0, 0, 0, 0);
    margin-bottom: 8px;
  }
}
</style>
