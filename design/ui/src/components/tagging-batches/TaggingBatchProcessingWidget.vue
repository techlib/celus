<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml" src="@/locales/dialog.yaml"></i18n>
<i18n lang="yaml">
en:
  select_tag: Select a tag to be assigned to all matched titles.
  annotated_file_hint: You can use the annotated file to inspect exactly which titles were matched by each row in the uploaded file.
  intro_message: Upload a CSV file containing one title per line. The file should contain columns identifying the title. Currently ISBN, ISSN and eISSN are supported.
  preprocessing_message: The file is being preprocessed. This may take a while.

cs:
  select_tag: Vyberte štítek, který bude přiřazen všem nalezeným titulům.
  annotated_file_hint: Pomocí anotovaného zdrojového souboru získáte detailní přehled, jaké tituly byly nalezeny pro jednotlivé řádky v nahraném souboru.
  intro_message: Nahrajte CSV soubor s jedním titulem na řádek. Soubor by měl obsahovat sloupce, které identifikují titul. Nyní je podporováno ISBN, ISSN a eISSN.
  preprocessing_message: Soubor se právě předzpracovává. Může to chvíli trvat.
</i18n>

<template>
  <v-form>
    <v-card>
      <v-card-title
        >{{
          batch ? $t("tagging.title_list") : $t("tagging.create_new_title_list")
        }}
      </v-card-title>
      <v-card-text>
        <v-row v-if="!taggingBatch">
          <v-col>{{ $t("intro_message") }}</v-col>
        </v-row>
        <v-row v-if="!taggingBatch">
          <v-col>
            <v-file-input
              v-model="dataFile"
              :label="$t('labels.source_file')"
              show-size
              prepend-icon="fa fa-list-alt"
              required
            />
          </v-col>
          <v-col cols="auto" class="align-self-center">
            <v-btn @click="upload()" color="primary" :disabled="!dataFile"
              >{{ $t("actions.upload_data") }}
            </v-btn>
          </v-col>
        </v-row>

        <v-row v-else-if="taggingBatch.state === 'preprocessing'">
          <v-col cols="12">
            {{ $t("preprocessing_message") }}
          </v-col>
          <v-col>
            <ServerTaskMonitor
              v-if="task"
              :value="task"
              @finished="taskFinished()"
              ref="taskMonitor"
            >
              {{ $t("tagging.preprocessing_data") }}
            </ServerTaskMonitor>
            <v-progress-linear v-else indeterminate height="32px">
              {{ $t("tagging.preprocessing_data") }}
            </v-progress-linear>
          </v-col>
        </v-row>

        <div v-else>
          <v-row>
            <v-col>
              <v-card elevation="1">
                <v-card-text>
                  <TaggingBatchPreflightInfo
                    :tagging-batch="taggingBatch"
                    show-file-name
                    full-width
                  />
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>

          <v-row>
            <v-col>
              <v-alert v-if="taggingBatch.annotated_file" type="info" outlined>
                {{ $t("annotated_file_hint") }}
              </v-alert>
            </v-col>
          </v-row>

          <div v-if="taggingBatch.state === 'preflight'">
            <v-row class="mt-4 mx-1">
              <v-col>{{ $t("select_tag") }}</v-col>
            </v-row>
            <v-row class="mt-0 mx-1">
              <v-col class="pt-0">
                <TagSelector v-model="tag" scope="title" single-tag />
              </v-col>
              <v-col cols="auto" class="align-self-center">
                <v-btn @click="assignTag()" color="primary" :disabled="!tag"
                  >{{ $t("actions.assign_tag") }}
                </v-btn>
              </v-col>
            </v-row>
          </div>

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
                  :value="task"
                  @finished="taskFinished()"
                  ref="taskMonitor"
                >
                  {{ $t("tag_state." + taggingBatch.state) }}
                </ServerTaskMonitor>
                <v-progress-linear v-else indeterminate height="32px">
                  {{ $t("tag_state." + taggingBatch.state) }}
                </v-progress-linear>
              </v-col>
            </v-row>
          </div>
        </div>
      </v-card-text>
      <v-card-actions class="pa-4">
        <v-tooltip
          bottom
          v-if="taggingBatch && taggingBatch.state === 'imported'"
        >
          <template #activator="{ on }">
            <v-btn @click="unassign()" color="error" v-on="on">
              {{ $t("tagging.unassign_tag") }}
            </v-btn>
          </template>
          <span>{{ $t("tagging.unassign_tag_tt") }}</span>
        </v-tooltip>
        <v-spacer />
        <v-btn @click="$emit('close')">{{ $t("actions.close") }}</v-btn>
      </v-card-actions>
    </v-card>
  </v-form>
</template>

<script>
import cancellation from "@/mixins/cancellation";
import { mapActions } from "vuex";
import TaggingBatchPreflightInfo from "@/components/tagging-batches/TaggingBatchPreflightInfo";
import TagSelector from "@/components/tags/TagSelector";
import ServerTask from "@/libs/server-task";
import ServerTaskMonitor from "@/components/tasks/ServerTaskMonitor";

export default {
  name: "TaggingBatchProcessingWidget",
  components: { ServerTaskMonitor, TagSelector, TaggingBatchPreflightInfo },
  mixins: [cancellation],

  props: {
    batch: { required: false, type: Object, default: null },
  },

  data() {
    return {
      taggingBatch: this.batch,
      dataFile: null,
      uploading: false,
      tag: this.batch?.tag,
      task: null,
    };
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
      this.uploading = true;
      let result = await this.http({
        url: "/api/tags/tagging-batch/",
        method: "POST",
        data: formData,
        headers: { "Content-Type": "multipart/form-data" },
      });
      if (!result.error) {
        this.taggingBatch = result.response.data;
        await this.startPreflight();
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
        data: {
          tag: this.tag.pk ?? this.tag, // it is sometimes an object, sometimes pk
        },
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
          this.taggingBatch?.state
        )
      ) {
        await this.fetchBatch();
        setTimeout(this.refreshBatch, 1000);
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
    cleanup() {
      // for some reason the watcher below doesn't work all the time,
      // so we have this explicit method here to clean up the batch
      this.taggingBatch = null;
      this.task = null;
      if (this.$refs.taskMonitor) {
        this.$refs.taskMonitor.stop();
      }
    },
    async taskFinished() {
      this.task = null;
      await this.refreshBatch();
    },
  },

  watch: {
    batch: {
      deep: true,
      handler() {
        this.taggingBatch = this.batch;
        if (this.taggingBatch) {
          this.tag = this.taggingBatch.tag;
        }
        this.refreshBatch();
      },
    },
  },
};
</script>

<style scoped></style>
