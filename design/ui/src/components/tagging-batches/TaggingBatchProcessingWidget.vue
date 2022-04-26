<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml" src="@/locales/dialog.yaml"></i18n>
<i18n lang="yaml">
en:
  select_tag: Select a tag to be assigned to all matched titles.
  annotated_file_hint: You can use the annotated file to inspect exactly which titles were matched by each row in the uploaded file.

cs:
  select_tag: Vyberte štítek, který bude přiřazen všem nalezeným titulům.
  annotated_file_hint: Pomocí anotovaného zdrojového souboru získáte detailní přehled, jaké tituly byly nalezeny pro jednotlivé řádky v nahraném souboru.
</i18n>

<template>
  <v-form>
    <v-card>
      <v-card-title>{{
        batch ? $t("tagging.title_list") : $t("tagging.create_new_title_list")
      }}</v-card-title>
      <v-card-text>
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
            <v-btn @click="upload()" color="primary" :disabled="!dataFile">{{
              $t("actions.upload_data")
            }}</v-btn>
          </v-col>
        </v-row>

        <v-row v-else-if="taggingBatch.state === 'initial'">
          <v-col>
            <v-progress-linear indeterminate height="24px">
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
                <v-btn @click="assignTag()" color="primary" :disabled="!tag">{{
                  $t("actions.assign_tag")
                }}</v-btn>
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
                <v-progress-linear indeterminate height="24px">
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
import axios from "axios";
import { mapActions } from "vuex";
import TaggingBatchPreflightInfo from "@/components/tagging-batches/TaggingBatchPreflightInfo";
import TagSelector from "@/components/tags/TagSelector";

export default {
  name: "TaggingBatchProcessingWidget",
  components: { TagSelector, TaggingBatchPreflightInfo },
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
      try {
        let response = await axios.post("/api/tags/tagging-batch/", formData, {
          headers: { "Content-Type": "multipart/form-data" },
        });
        this.taggingBatch = response.data;
        await this.refreshBatch();
      } catch (error) {
        this.showSnackbar({ content: "Could not upload file", color: "error" });
      } finally {
        this.uploading = false;
      }
    },
    async assignTag() {
      try {
        const resp = await axios.post(
          `/api/tags/tagging-batch/${this.taggingBatch.pk}/assign-tags/`,
          {
            tag: this.tag.pk ?? this.tag,
          }
        );
        this.taggingBatch = resp.data.batch;
        await this.refreshBatch();
      } catch (error) {
        this.showSnackbar({ content: "Could not assign tag", color: "error" });
      }
    },
    async refreshBatch() {
      if (
        this.taggingBatch?.state === "initial" ||
        this.taggingBatch?.state === "importing" ||
        this.taggingBatch?.state === "undoing"
      ) {
        await this.fetchBatch();
        setTimeout(this.refreshBatch, 1000);
      }
    },
    async unassign() {
      try {
        const resp = await axios.post(
          `/api/tags/tagging-batch/${this.taggingBatch.pk}/unassign/`
        );
        this.taggingBatch = resp.data.batch;
        await this.refreshBatch();
      } catch (error) {
        this.showSnackbar({
          content: "Could not unassign tag",
          color: "error",
        });
      }
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
