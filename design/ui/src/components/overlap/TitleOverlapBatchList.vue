<i18n src="@/locales/common.yaml" lang="yaml"></i18n>
<i18n src="@/locales/dialog.yaml" lang="yaml"></i18n>

<i18n lang="yaml">
en:
  matched_rows: Matched rows
  total_rows: Total rows
  delete_batch_tt: Delete this file from CELUS
  delete_batch_text: Are you sure you want to delete this file?
  batch_deleted: File was successfully deleted.
  annotated_file_tt: Download annotated file
  source_file_tt: Download copy of the source file
  unicode_error: There was an error with the file encoding. Please make sure that the file is encoded in UTF-8. See the linked support article for more information.
  support_link: How to prepare the input file

cs:
  matched_rows: Nalezené řádky
  total_rows: Celkem řádků
  delete_batch_tt: Odstranit tento soubor z CELUSu
  delete_batch_text: Opravdu chcete odstranit tento soubor?
  batch_deleted: Soubor byl úspěšně odstraněn.
  annotated_file_tt: Stáhnout anotovaný soubor
  source_file_tt: Stáhnout kopii zdrojového souboru
  unicode_error: Došlo k chybě s kódováním souboru. Ujistěte se, že je soubor kódován v UTF-8. Více informací naleznete v odkazovaném článku.
  support_link: Jak připravit vstupní soubor
</i18n>

<template>
  <div>
    <v-data-table
      :items="batches"
      :loading="loading"
      item-key="pk"
      :headers="headers"
      v-model:sort-by="orderBy"
      density="comfortable"
    >
      <template #top>
        <v-btn color="primary" width="290px" @click="showUploadDialog = true">
          <v-icon size="small" class="me-2">fa fa-upload</v-icon>
          {{ $t("actions.upload_file_for_annotation") }}
        </v-btn>
      </template>
      <template #item.created="{ item }">
        <v-tooltip location="bottom">
          <template #activator="{ props }">
            <span v-bind="props">{{ relativeDate(item.created) }}</span>
          </template>
          <span>{{ isoDateTimeFormat(item.created) }}</span>
        </v-tooltip>
      </template>
      <template #item.state="{ item }">
        <!-- processing -->
        <ServerTaskMonitor
          v-if="item.state === 'processing' && item.task"
          dense
          @finished="refetchBatch(item.pk)"
          :model-value="item.task"
        ></ServerTaskMonitor>
        <!-- failed -->
        <v-tooltip
          location="bottom"
          v-else-if="item.state === 'failed'"
          max-width="600"
        >
          <template #activator="{ props }">
            <span v-bind="props">
              <v-icon color="error" size="small"
                >fa fa-exclamation-circle</v-icon
              >
              <a
                v-if="isUnicodeError(item.processing_info.error)"
                class="ms-1 text-caption font-weight-bold"
                target="_blank"
                href="https://support.celus.net/support/solutions/articles/103000062844"
              >
                {{ $t("support_link") }}
              </a>
            </span>
          </template>
          <span>
            <span class="font-weight-bold">{{ $t("labels.error") }}:</span>
            {{
              isUnicodeError(item.processing_info.error)
                ? $t("unicode_error")
                : item.processing_info.error
            }}
          </span>
        </v-tooltip>
        <!-- other states -->
        <v-tooltip location="bottom" v-else>
          <template #activator="{ props }">
            <v-icon
              :color="stateToColor(item.state)"
              size="small"
              v-bind="props"
            >
              {{ stateToIcon(item.state) }}
            </v-icon>
          </template>
          {{ item.state }}
        </v-tooltip>
      </template>
      <template #item.source_file="{ item }">
        <v-tooltip location="bottom">
          <template #activator="{ props }">
            <a :href="item.source_file" target="_blank" v-bind="props">
              <v-icon size="small">fa fa-file</v-icon>
            </a>
          </template>
          <span>{{ $t("source_file_tt") }}</span>
        </v-tooltip>
      </template>
      <template #item.annotated_file="{ item }">
        <v-tooltip location="bottom" v-if="item.annotated_file">
          <template #activator="{ props }">
            <a :href="item.annotated_file" target="_blank" v-bind="props">
              <v-icon
                size="small"
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
            (item.processing_info.stats.no_match ?? 0)
          }}
          /
          {{ item.processing_info.stats.row_count }}
        </span>
        <span v-else>-</span>
      </template>
      <template #item.actions="{ item }">
        <v-tooltip location="bottom">
          <template #activator="{ props }">
            <v-btn
              icon="fa fa-trash"
              density="comfortable"
              variant="text"
              @click="deleteBatch(item.pk)"
              color="error"
              v-bind="props"
              class="delete_btn"
            >
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
    ></TitleOverlapUploadFileDialog>
  </div>
</template>

<script>
import TitleOverlapUploadFileDialog from "@/components/overlap/TitleOverlapUploadFileDialog";
import ServerTaskMonitor from "@/components/tasks/ServerTaskMonitor.vue";
import {
  isoDateTimeFormat,
  isoDateTimeFormatSpans,
  parseDateTime,
} from "@/libs/dates";
import ServerTask from "@/libs/server-task";
import cancellation from "@/mixins/cancellation";
import { formatDistance } from "date-fns";
import { mapActions, mapGetters, mapState } from "vuex";

export default {
  name: "TitleOverlapBatchList",
  components: {
    TitleOverlapUploadFileDialog,
    ServerTaskMonitor,
  },

  mixins: [cancellation],

  data() {
    return {
      batches: [],
      loading: false,
      showUploadDialog: false,
      dataFile: null,
      now: null,
      timer: null,
      orderBy: [{ key: "created", order: "desc" }],
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
        { title: this.$t("labels.created"), value: "created", key: "created" },
        {
          title: this.$t("labels.organization"),
          value: "organization.name",
          key: "organization.name",
        },
        { title: this.$t("labels.status"), value: "state", key: "state" },
        {
          title: this.$t("matched_rows"),
          value: "matched_rows",
          sortable: false,
        },
        {
          title: this.$t("labels.source_file"),
          value: "source_file",
          sortable: false,
        },
        {
          title: this.$t("labels.annotated_file"),
          value: "annotated_file",
          sortable: false,
        },
        {
          title: this.$t("title_fields.actions"),
          value: "actions",
          sortable: false,
        },
      ];
    },
  },

  methods: {
    isoDateTimeFormat,
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
        color: "warning",
        icon: "fa fa-warning",
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
          return "fas fa-clock";
        case "done":
          return "fa fa-check-circle";
        case "failed":
          return "fa fa-exclamation-circle";
        default:
          return "fa fa-question-circle";
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
    isUnicodeError(error) {
      return error?.includes("utf-8") && error?.includes("codec");
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

  beforeUnmount() {
    clearTimeout(this.timer);
  },
};
</script>

<style scoped lang="scss">
.delete_btn {
  :deep(.v-icon) {
    font-size: 18px;
  }
}
</style>
