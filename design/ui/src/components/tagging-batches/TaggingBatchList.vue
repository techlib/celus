<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<i18n lang="yaml" src="@/locales/dialog.yaml"></i18n>

<template>
  <div>
    <v-skeleton-loader v-if="loading" type="table"></v-skeleton-loader>
    <v-data-table
      v-else
      :items="visibleTaggingBatches"
      :headers="headers"
      item-key="pk"
      item-value="pk"
      v-model:sort-by="orderBy"
      density="default"
      v-model:page="page"
      v-model:items-per-page="itemsPerPage"
      :footer-props="{ itemsPerPageOptions: [10, 25, 50] }"
      v-model:expanded="expanded"
      expand-icon="fas fa-caret-down"
    >
      <template #top>
        <div class="d-flex px-1 align-center">
          <v-btn color="primary" @click="uploadNew()">
            <v-icon size="small" class="pr-6">fa fa-upload</v-icon>
            {{ $t("tagging.create_new_title_list") }}
          </v-btn>
          <v-spacer></v-spacer>
          <v-switch
            v-model="onlyMy"
            :label="$t('tagging.show_only_my')"
            class="d-flex align-start justify-end"
            color="primary"
            style="min-width: 115px"
          ></v-switch>
        </div>
      </template>
      <template #[`item.created`]="{ item }">
        <span v-html="formatDate(item.created)"></span>
      </template>
      <template #[`item.state`]="{ item }">
        <TaggingBatchStateWidget :batch="item"></TaggingBatchStateWidget>
      </template>
      <template #[`item.tag`]="{ item }">
        <TagChip v-if="item.tag" :tag="item.tag" show-class link></TagChip>
        <span v-else-if="item.tag_class">{{
          $t("tagging.tags_read_from_file")
        }}</span>
      </template>
      <template #[`item.preflight.rows_total`]="{ item, value }">
        <v-tooltip location="bottom">
          <template #activator="{ props }">
            <span v-bind="props">{{ formatInteger(value) }}</span>
          </template>
          {{ $t("tagging.data_rows_tt") }}
        </v-tooltip>
      </template>
      <template #[`item.preflight.unique_matched_titles`]="{ item }">
        <v-tooltip
          v-if="item.import_count > 1"
          location="bottom"
          max-width="600px"
        >
          <template #activator="{ props }">
            <v-icon v-bind="props" size="x-small" color="info" class="mr-2"
              >fa fa-info-circle</v-icon
            >
          </template>
          {{ $t("tagging.multi_import_tt") }}
        </v-tooltip>
        <v-tooltip location="bottom">
          <template #activator="{ props }">
            <span v-bind="props">{{
              formatInteger(
                item.state === "imported"
                  ? item.postflight?.tagged_titles
                  : item.preflight?.unique_matched_titles,
              )
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
              (item.postflight?.tagged_titles || 0) <
                (item.postflight?.unique_matched_titles || 0)
                ? $t("tagging.tagged_titles_note")
                : $t("tagging.title_number_note")
            }}
          </div>
        </v-tooltip>
      </template>
      <template #[`item.actions`]="{ item }">
        <v-tooltip location="bottom">
          <template #activator="{ props }">
            <v-btn
              @click="openBatch(item)"
              icon
              size="small"
              variant="text"
              v-bind="props"
              color="lighterIcons"
              density="comfortable"
            >
              <v-icon size="small">fa fa-cog</v-icon>
            </v-btn>
          </template>
          {{ $t("tagging.manage") }}
        </v-tooltip>
        <v-tooltip location="bottom">
          <template #activator="{ props }">
            <v-btn
              @click="deleteBatch(item)"
              density="comfortable"
              icon
              size="small"
              variant="text"
              v-bind="props"
              color="lighterIcons"
            >
              <v-icon size="small">fa fa-trash</v-icon>
            </v-btn>
          </template>
          {{ $t("actions.delete") }}
        </v-tooltip>
      </template>
      <template v-slot:expanded-row="{ item, columns }">
        <tr class="item_expanded_space">
          <td :colspan="columns.length" class="px-0">
            <v-sheet class="ma-2 text--secondary">
              <TaggingBatchStats
                :tagging-batch="item"
                show-file-name
                show-attempts
              ></TaggingBatchStats>
            </v-sheet>
          </td>
        </tr>
      </template>
      <template #[`item.last_updated_by`]="{ item }">
        {{ userToString(item.last_updated_by) }}
      </template>
    </v-data-table>
    <v-dialog v-model="showDialog" v-if="showDialog" max-width="720px">
      <TaggingBatchProcessingWidget
        :batch="selectedBatch"
        @close="hideDialog"
      ></TaggingBatchProcessingWidget>
    </v-dialog>
  </div>
</template>

<script>
import cancellation from "@/mixins/cancellation";
import TaggingBatchProcessingWidget from "@/components/tagging-batches/TaggingBatchProcessingWidget";
import { isoDateTimeFormatSpans, parseDateTime } from "@/libs/dates";
import TagChip from "@/components/tags/TagChip";
import TaggingBatchStats from "@/components/tagging-batches/TaggingBatchStats";
import { mapActions, mapState } from "vuex";
import stateTracking from "@/mixins/stateTracking";
import TaggingBatchStateWidget from "@/components/tagging-batches/TaggingBatchStateWidget.vue";
import { formatInteger } from "@/libs/numbers";
import { userToString } from "../../libs/user";

export default {
  name: "TaggingBatchList",
  components: {
    TaggingBatchStateWidget,
    TaggingBatchStats,
    TagChip,
    TaggingBatchProcessingWidget,
  },
  mixins: [cancellation, stateTracking],

  data() {
    return {
      taggingBatches: [],
      selectedBatch: null,
      showDialog: false,
      expanded: [],
      loading: false,
      onlyMy: false,
      // table state
      orderBy: [{ key: "created", order: this.orderDesc ? "asc" : "desc" }],
      orderDesc: true,
      page: 1,
      itemsPerPage: 25,
      // state tracking support
      watchedAttrs: [
        {
          name: "orderBy",
          type: Object,
        },
        {
          name: "orderDesc",
          type: Boolean,
        },
        {
          name: "page",
          type: Number,
        },
        {
          name: "itemsPerPage",
          type: Number,
          var: "ipp",
        },
        {
          name: "onlyMy",
          type: Boolean,
        },
      ],
    };
  },

  computed: {
    ...mapState({
      user: "user",
    }),
    headers() {
      return [
        {
          title: "",
          value: "data-table-expand",
          sortable: false,
          align: "start",
        },
        {
          title: this.$i18n.t("labels.created"),
          value: "created",
          key: "created",
        },
        {
          title: this.$i18n.t("labels.last_updated_by"),
          value: "last_updated_by",
          key: "last_updated_by",
        },
        {
          title: this.$i18n.t("labels.state"),
          value: "state",
          key: "state",
        },
        {
          title: this.$i18n.t("labels.tag"),
          value: "tag",
          key: "tag",
        },
        {
          title: this.$i18n.t("labels.rows"),
          value: "preflight.rows_total",
          align: "end",
          key: "preflight.rows_total",
        },
        {
          title: this.$i18n.t("titles"),
          value: "preflight.unique_matched_titles",
          align: "end",
          key: "preflight.unique_matched_titles",
        },
        {
          title: this.$i18n.t("title_fields.actions"),
          value: "actions",
          sortable: false,
          key: "actions",
        },
      ];
    },
    visibleTaggingBatches() {
      let batches = this.taggingBatches;
      if (this.onlyMy) {
        batches = batches.filter(
          (batch) => batch.last_updated_by.pk === this.user.pk,
        );
      }
      return batches;
    },
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    formatInteger,
    userToString,
    async fetchTaggingBatches() {
      this.loading = true;
      const result = await this.http({ url: "/api/tags/tagging-batch/" });
      if (!result.error) {
        this.taggingBatches = result.response.data;
      }
      this.loading = false;
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
        color: "warning",
        icon: "fa fa-warning",
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
            (batch) => batch.pk !== item.pk,
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
