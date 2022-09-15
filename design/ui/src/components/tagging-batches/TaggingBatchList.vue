<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml" src="@/locales/dialog.yaml" />

<template>
  <div>
    <v-data-table
      :items="taggingBatches"
      :headers="headers"
      item-key="pk"
      sort-by="created"
      sort-desc
      show-expand
      :expanded.sync="expanded"
      expand-icon="fa fa-caret-down"
    >
      <template #top>
        <v-btn color="primary" @click="uploadNew()">
          <v-icon small class="pr-2">fa fa-upload</v-icon>
          {{ $t("tagging.create_new_title_list") }}
        </v-btn>
      </template>

      <template #item.created="{ item }">
        <span v-html="formatDate(item.created)" />
      </template>

      <template #item.state="{ item }">
        <TaggingBatchStateIcon :batch="item" />
        <span>{{ $t("tag_state." + item.state) }}</span>
      </template>

      <template #item.tag="{ item }">
        <TagChip v-if="item.tag" :tag="item.tag" show-class link />
      </template>

      <template #item.preflight.stats.row_count="{ item, value }">
        <v-tooltip bottom>
          <template #activator="{ on }">
            <span v-on="on">{{ value }}</span>
          </template>
          {{ $t("tagging.data_rows_tt") }}
        </v-tooltip>
      </template>

      <template #item.preflight.stats.unique_matched_titles="{ item }">
        <v-tooltip bottom>
          <template #activator="{ on }">
            <span v-on="on">{{
              item.state === "imported"
                ? item.postflight?.stats?.tagged_titles
                : item.preflight?.stats?.unique_matched_titles
            }}</span>
          </template>
          <div>
            {{
              item.state === "imported"
                ? $t("tagging.tagged_titles_tt")
                : $t("tagging.matched_titles_tt")
            }}
          </div>
          <div>
            {{
              item.state === "imported" &&
              (item.postflight?.stats?.tagged_titles || 0) <
                (item.postflight?.stats?.unique_matched_titles || 0)
                ? $t("tagging.tagged_titles_note")
                : $t("tagging.title_number_note")
            }}
          </div>
        </v-tooltip>
      </template>

      <template #item.actions="{ item }">
        <v-tooltip bottom>
          <template #activator="{ on }">
            <v-btn @click="openBatch(item)" icon small v-on="on">
              <v-icon small>fa fa-edit</v-icon>
            </v-btn>
          </template>
          {{ $t("actions.edit") }}
        </v-tooltip>

        <v-tooltip bottom>
          <template #activator="{ on }">
            <v-btn @click="deleteBatch(item)" icon small v-on="on">
              <v-icon small>fa fa-trash</v-icon>
            </v-btn>
          </template>
          {{ $t("actions.delete") }}
        </v-tooltip>
      </template>

      <template #expanded-item="{ item, headers }">
        <td :colspan="headers.length" class="px-0">
          <v-sheet class="ma-2 text--secondary">
            <TaggingBatchStats :tagging-batch="item" show-file-name />
          </v-sheet>
        </td>
      </template>
    </v-data-table>
    <v-dialog v-model="showDialog" v-if="showDialog" max-width="720px">
      <TaggingBatchProcessingWidget
        :batch="selectedBatch"
        @close="hideDialog"
      />
    </v-dialog>
  </div>
</template>

<script>
import cancellation from "@/mixins/cancellation";
import TaggingBatchProcessingWidget from "@/components/tagging-batches/TaggingBatchProcessingWidget";
import { isoDateTimeFormatSpans, parseDateTime } from "@/libs/dates";
import TagChip from "@/components/tags/TagChip";
import TaggingBatchStats from "@/components/tagging-batches/TaggingBatchStats";
import TaggingBatchStateIcon from "@/components/tagging-batches/TaggingBatchStateIcon";
import { mapActions } from "vuex";

export default {
  name: "TaggingBatchList",
  components: {
    TaggingBatchStateIcon,
    TaggingBatchStats,
    TagChip,
    TaggingBatchProcessingWidget,
  },
  mixins: [cancellation],

  data() {
    return {
      taggingBatches: [],
      selectedBatch: null,
      showDialog: false,
      expanded: [],
    };
  },

  computed: {
    headers() {
      return [
        {
          text: this.$i18n.t("labels.created"),
          value: "created",
        },
        {
          text: this.$i18n.t("labels.state"),
          value: "state",
        },
        {
          text: this.$i18n.t("labels.tag"),
          value: "tag",
        },
        {
          text: this.$i18n.t("labels.rows"),
          value: "preflight.stats.row_count",
        },
        {
          text: this.$i18n.t("titles"),
          value: "preflight.stats.unique_matched_titles",
        },
        {
          text: this.$i18n.t("title_fields.actions"),
          value: "actions",
          sortable: false,
        },
      ];
    },
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    async fetchTaggingBatches() {
      const result = await this.http({ url: "/api/tags/tagging-batch/" });
      if (!result.error) {
        this.taggingBatches = result.response.data;
      }
    },
    formatDate(date) {
      return isoDateTimeFormatSpans(parseDateTime(date));
    },
    hideDialog() {
      this.showDialog = false;
      this.selectedBatch = null;
      this.fetchTaggingBatches();
    },
    async deleteBatch(item) {
      const goOn = await this.$confirm(this.$t("tagging.delete_batch_text"), {
        title: this.$t("confirm_delete"),
        buttonTrueText: this.$t("actions.delete"),
        buttonFalseText: this.$t("actions.cancel"),
      });
      if (goOn) {
        const reply = await this.http({
          url: `/api/tags/tagging-batch/${item.pk}/`,
          method: "delete",
        });
        if (!reply.error) {
          this.showSnackbar({
            content: this.$t("tagging.batch_delete_success"),
            color: "success",
          });
          this.taggingBatches = this.taggingBatches.filter(
            (batch) => batch.pk !== item.pk
          );
        }
      }
    },
    uploadNew() {
      this.selectedBatch = null;
      this.showDialog = true;
    },
    openBatch(item) {
      this.selectedBatch = item;
      this.showDialog = true;
    },
  },

  mounted() {
    this.fetchTaggingBatches();
  },
};
</script>

<style scoped></style>
