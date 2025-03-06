<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<i18n lang="yaml" src="@/locales/dialog.yaml"></i18n>

<i18n lang="yaml">
en:
  assign_tag_header: After reviewing the preprocessing results, you can assign the selected tag to all matched titles.
  assign_tags_header: After reviewing the preprocessing results, you can assign matched tags to corresponding titles.
  select_tag: Select a tag to be assigned to all matched titles.
  annotated_file_hint: You can use the annotated file to inspect exactly which titles were matched by each row in the uploaded file.
  intro_message: Upload a CSV file containing one title per line. The file should contain columns identifying the title. Currently ISBN, ISSN, eISSN and "Proprietary ID" are supported column names. In case you want to load the tag names from the file as well, it should also contain a column named "tag".
  preprocessing_message: The file is being preprocessed. This may take a while.
  tag_with_one_tag: Tag all titles with one tag
  get_tag_from_file: Get tag names from the input file
  tag_source: Tag source
  select_class: Select tag class for uploaded tags

cs:
  assign_tag_header: Po kontrole předzpracovaných výsledků můžete přiřadit vybrané štítky ke všem nalezeným titulům.
  assign_tags_header: Po kontrole předzpracovaných výsledků můžete přiřadit nalezené štítky ke všem odpovídajícím titulům.
  select_tag: Vyberte štítek, který bude přiřazen všem nalezeným titulům.
  annotated_file_hint: Pomocí anotovaného zdrojového souboru získáte detailní přehled, jaké tituly byly nalezeny pro jednotlivé řádky v nahraném souboru.
  intro_message: Nahrajte CSV soubor s jedním titulem na řádek. Soubor by měl obsahovat sloupce, které identifikují titul. Jsou podporovány jména sloupců ISBN, ISSN, eISSN a "Proprietary ID". Pokud chcete načíst i názvy štítků ze souboru, musí obsahovat i sloupec s názvem "tag".
  preprocessing_message: Soubor se právě předzpracovává. Může to chvíli trvat.
  tag_with_one_tag: Všechny tituly s jedním štítkem
  get_tag_from_file: Získat jména štítků přímo ze souboru
  tag_source: Zdroj štítků
  select_class: Vyberte typ nahraných štítků
</i18n>

<template>
  <v-form>
    <v-card>
      <v-card-title class="pt-4"
        >{{
          batch ? $t("tagging.title_list") : $t("tagging.create_new_title_list")
        }}
      </v-card-title>
      <v-card-text>
        <v-row v-if="!taggingBatch">
          <v-col :class="batch ? '' : 'intro_new'">{{
            $t("intro_message")
          }}</v-col>
        </v-row>
        <v-row>
          <v-col>
            <v-radio-group
              v-model="getTagsFromFile"
              inline
              :label="$t('tag_source') + ':'"
              :disabled="!!taggingBatch"
              class="tag_group"
            >
              <v-radio :label="$t('tag_with_one_tag')" :value="false"></v-radio>
              <v-radio :label="$t('get_tag_from_file')" :value="true"></v-radio>
            </v-radio-group>
          </v-col>
        </v-row>
        <!-- no batch -->
        <v-row v-if="!taggingBatch">
          <v-col v-if="getTagsFromFile">
            <TagClassSelector
              scope="title"
              v-model="tagClass"
              :label="$t('select_class')"
              allow-create
              show-icon
            ></TagClassSelector>
          </v-col>
          <v-col v-if="!getTagsFromFile">
            <TagSelector
              scope="title"
              v-model="tag"
              :label="$t('select_tag')"
              show-icon
              single-tag
              assignable-only
              dont-check-exclusive
              allow-create
            ></TagSelector>
          </v-col>
        </v-row>
        <v-row v-if="!taggingBatch">
          <v-col>
            <v-file-input
              v-model="dataFile"
              :label="$t('labels.source_file')"
              show-size
              required
              variant="underlined"
              prepend-icon="fa fa-list-alt"
              hide-details
            ></v-file-input>
          </v-col>
          <v-col cols="auto" class="align-self-center">
            <v-btn @click="upload()" color="primary" :disabled="!canUpload"
              >{{ $t("actions.upload_data") }}
            </v-btn>
          </v-col>
        </v-row>
        <!-- preprocessing stage -->
        <v-row v-else-if="taggingBatch.state === 'preprocessing'">
          <v-col cols="12">
            {{ $t("preprocessing_message") }}
          </v-col>
          <v-col>
            <ServerTaskMonitor
              v-if="task"
              @finished="taskFinished()"
              ref="taskMonitor"
              :model-value="task"
            >
              {{ $t("tagging.preprocessing_data") }}
            </ServerTaskMonitor>
            <v-progress-linear
              v-else
              indeterminate
              height="32px"
              color="primary"
            >
              {{ $t("tagging.preprocessing_data") }}
            </v-progress-linear>
          </v-col>
        </v-row>
        <!-- any other stage -->
        <div v-else>
          <v-row>
            <v-col>
              <v-card elevation="1">
                <v-card-text style="overflow-x: auto">
                  <TaggingBatchStats
                    :tagging-batch="taggingBatch"
                    show-file-name
                    full-width
                  ></TaggingBatchStats>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>
          <v-row>
            <v-col>
              <v-alert
                v-if="taggingBatch.annotated_file && canAssign"
                type="info"
                variant="outlined"
                class="mb-0"
              >
                {{ $t("annotated_file_hint") }}
              </v-alert>
            </v-col>
          </v-row>
          <!-- preflight done - we can show assign button -->
          <div v-if="taggingBatch.state === 'preflight' && canAssign">
            <v-row class="mt-4 mx-0">
              <v-col class="px-1 assign_tag">{{
                getTagsFromFile
                  ? $t("assign_tags_header")
                  : $t("assign_tag_header")
              }}</v-col>
            </v-row>
          </div>
          <!-- something is currently going on with the batch -->
          <div
            v-else-if="
              taggingBatch.state === 'importing' ||
              taggingBatch.state === 'undoing'
            "
          >
            <v-row>
              <v-col>
                <ServerTaskMonitor
                  v-if="task"
                  @finished="taskFinished()"
                  ref="taskMonitor"
                  :model-value="task"
                >
                  {{ $t("tag_state." + taggingBatch.state) }}
                </ServerTaskMonitor>
                <v-progress-linear
                  v-else
                  color="primary"
                  indeterminate
                  height="32px"
                  :buffer-value="100 * taggingBatch.state"
                >
                  {{ $t("tag_state." + taggingBatch.state) }}
                </v-progress-linear>
              </v-col>
            </v-row>
          </div>
          <!-- batch is imported -->
          <v-row v-else-if="taggingBatch.state === 'imported'">
            <v-col>
              <v-switch
                v-model="automaticReprocessing"
                :label="$t('tagging.automatic_reprocessing')"
                :hint="$t('tagging.automatic_reprocessing_tt')"
                persistent-hint
                color="primary"
                class="pt-0 mt-0 mx-2"
              ></v-switch>
            </v-col>
          </v-row>
        </div>
      </v-card-text>
      <v-card-actions class="pa-4 mt-4">
        <!-- assign button -->
        <span
          v-if="taggingBatch && taggingBatch.state === 'preflight' && canAssign"
        >
          <v-btn
            v-if="getTagsFromFile"
            variant="flat"
            elevation="2"
            color="primary"
            @click="assignTag()"
          >
            {{ $t("actions.assign_tags") }}
          </v-btn>
          <v-btn
            v-else
            @click="assignTag()"
            color="primary"
            :disabled="!tag"
            variant="flat"
            elevation="2"
            >{{ $t("actions.assign_tag") }}
          </v-btn>
        </span>
        <!-- unassign button -->
        <v-tooltip
          location="bottom"
          v-else-if="taggingBatch && taggingBatch.state === 'imported'"
        >
          <template #activator="{ props }">
            <v-btn
              @click="unassign()"
              variant="flat"
              elevation="2"
              color="error"
              v-bind="props"
            >
              <v-icon size="x-small" class="mr-1">fa fa-trash</v-icon>
              {{ $t("tagging.unassign_tag") }}
            </v-btn>
          </template>
          <span>{{ $t("tagging.unassign_tag_tt") }}</span>
        </v-tooltip>
        <v-spacer></v-spacer>
        <v-tooltip
          location="bottom"
          v-if="taggingBatch && taggingBatch.state === 'imported'"
        >
          <template #activator="{ props }">
            <v-btn
              @click="assignTag()"
              v-bind="props"
              variant="flat"
              elevation="2"
            >
              <v-icon size="x-small" class="mr-1">fa fa-redo-alt</v-icon>
              {{ $t("tagging.reassign_tag") }}
            </v-btn>
          </template>
          <span>{{ $t("tagging.reassign_tag_tt") }}</span>
        </v-tooltip>
        <v-btn
          @click="$emit('close')"
          variant="flat"
          elevation="2"
          color="primary"
          >{{ $t("actions.close") }}</v-btn
        >
      </v-card-actions>
    </v-card>
    <ErrorDialog
      v-if="showErrorDialog"
      v-model="showErrorDialog"
      :errors="errors"
    ></ErrorDialog>
  </v-form>
</template>

<script>
import cancellation from "@/mixins/cancellation";
import { mapActions } from "vuex";
import TagSelector from "@/components/tags/TagSelector";
import ServerTask from "@/libs/server-task";
import ServerTaskMonitor from "@/components/tasks/ServerTaskMonitor";
import TaggingBatchStats from "@/components/tagging-batches/TaggingBatchStats";
import ErrorDialog from "@/components/util/ErrorDialog";
import TagClassSelector from "@/components/tags/TagClassSelector.vue";

export default {
  name: "TaggingBatchProcessingWidget",
  components: {
    TagClassSelector,
    ErrorDialog,
    TaggingBatchStats,
    ServerTaskMonitor,
    TagSelector,
  },
  mixins: [cancellation],

  props: {
    batch: { required: false, type: Object, default: null },
  },

  data() {
    return {
      taggingBatch: this.batch,
      dataFile: null,
      uploading: false,
      tagClass: this.batch?.tag_class,
      tag: this.batch?.tag,
      task: null,
      timeout: null,
      showErrorDialog: false,
      errors: [],
      getTagsFromFile: this.batch ? !this.batch.tag : false,
    };
  },

  computed: {
    canUpload() {
      return !!(
        this.dataFile && (this.getTagsFromFile ? this.tagClass : this.tag)
      );
    },
    canAssign() {
      return this.taggingBatch?.preflight?.recognized_columns?.length > 0;
    },
    automaticReprocessing: {
      get() {
        return !!this.taggingBatch?.reprocess_after;
      },
      set(value) {
        this.setReprocessing(value);
      },
    },
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    async fetchBatch() {
      if (this.taggingBatch?.pk) {
        let result = await this.http({
          url: `/api/tags/tagging-batch/${this.taggingBatch.pk}/`,
        });
        if (!result.error) {
          this.taggingBatch = result.response.data;
        }
      }
    },
    async upload() {
      let formData = new FormData();
      formData.append("source_file", this.dataFile);
      if (this.getTagsFromFile) {
        formData.append("tag_class", this.tagClass.pk);
      } else {
        formData.append("tag", this.tag);
      }
      this.uploading = true;
      let result = await this.http({
        url: "/api/tags/tagging-batch/",
        method: "POST",
        data: formData,
        headers: { "Content-Type": "multipart/form-data" },
        errorTexts: { 413: this.$t("errors.file_too_large") },
      });
      if (!result.error) {
        this.taggingBatch = result.response.data;
        await this.startPreflight();
      } else {
        let info = result.error?.response?.data;
        if (info && typeof info === "object" && "source_file" in info) {
          this.showErrorDialog = true;
          this.errors = info.source_file;
        }
      }
      this.uploading = false;
    },
    async startPreflight() {
      let result = await this.http({
        url: `/api/tags/tagging-batch/${this.taggingBatch.pk}/preflight/`,
        method: "POST",
      });
      if (!result.error) {
        this.taggingBatch = result.response.data.batch;
        this.task = new ServerTask(result.response.data.task_id);
        await this.refreshBatch();
      }
    },
    async assignTag() {
      const result = await this.http({
        url: `/api/tags/tagging-batch/${this.taggingBatch.pk}/assign-tags/`,
        method: "POST",
      });
      if (!result.error) {
        this.taggingBatch = result.response.data.batch;
        this.task = new ServerTask(result.response.data.task_id);
        await this.refreshBatch();
      }
    },
    async refreshBatch() {
      if (
        !this.task &&
        ["preprocessing", "importing", "undoing"].includes(
          this.taggingBatch?.state,
        )
      ) {
        await this.fetchBatch();
        this.timeout = setTimeout(this.refreshBatch, 1000);
      } else {
        // no more refreshes
        this.timeout = null;
      }
    },
    async unassign() {
      const result = await this.http({
        url: `/api/tags/tagging-batch/${this.taggingBatch.pk}/unassign/`,
        method: "POST",
      });
      if (!result.error) {
        this.taggingBatch = result.response.data.batch;
        this.task = new ServerTask(result.response.data.task_id);
        await this.refreshBatch();
      }
    },
    async taskFinished() {
      this.task = null;
      await this.refreshBatch();
    },
    async setReprocessing(value) {
      const result = await this.http({
        method: "patch",
        url: `/api/tags/tagging-batch/${this.taggingBatch.pk}/`,
        data: {
          reprocess_after: value ? "30 days" : null,
        },
      });
      if (!result.error) {
        this.taggingBatch = result.response.data;
      }
    },
  },

  mounted() {
    this.refreshBatch();
  },

  beforeUnmount() {
    if (this.$refs.taskMonitor) {
      this.$refs.taskMonitor.stop();
    }
    if (this.timeout) {
      clearTimeout(this.timeout);
    }
  },
};
</script>

<style scoped>
.assign_tag {
  color: rgba(0, 0, 0, 0.6);
  font-size: 14px;
}
.intro_new {
  font-size: 14px;
  color: rgba(0, 0, 0, 0.6);
}

:deep(.v-input) {
  align-items: center;
}

:deep(.v-input__control) {
  flex-direction: row !important;
  align-items: center;
}
:deep(.v-selection-control-group) {
  margin-top: 0 !important;
}

:deep(.v-input__control) {
  height: 20px;
  min-height: 20px;
}
</style>
