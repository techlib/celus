<i18n lang="yaml">
en:
  tag_stats_tt: "Matched rows: {matched_lines}, matched titles: {matched_titles}"

cs:
  tag_stats_tt: "Odpovídajících řádků: {found}, nalezených titulů: {used}"
</i18n>

<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<template>
  <table
    class="overview"
    :class="{ 'full-width': fullWidth }"
    style="color: rgba(0, 0, 0, 0.6); font-size: 14px"
  >
    <tr>
      <th>{{ $t("labels.state") }}</th>
      <td class="text-right">
        <TaggingBatchStateWidget
          :batch="taggingBatch"
        ></TaggingBatchStateWidget>
      </td>
    </tr>
    <tr v-if="taggingBatch.tag">
      <th>{{ $t("labels.tag") }}</th>
      <td class="text-right">
        <TagChip :tag="taggingBatch.tag" show-class></TagChip>
      </td>
    </tr>
    <tr v-else-if="taggingBatch.tag_class">
      <th>{{ $t("labels.tag_class") }}</th>
      <td class="text-right">
        <TagChip :tag="taggingBatch.tag_class"></TagChip>
      </td>
    </tr>
    <tr v-if="taggingBatch.state === 'imported'">
      <th>{{ $t("tagging.automatic_reprocessing") }}</th>
      <td class="text-right">
        <!-- the key bellow is there to prevent the tooltip from disappearing
        on change, probably due to some bug in vuetify -->
        <v-tooltip
          location="bottom"
          max-width="600px"
          :key="'tt' + taggingBatch.reprocess_after"
        >
          <template #activator="{ props }">
            <span v-bind="props">{{
              taggingBatch.reprocess_after === null
                ? $t("labels.off")
                : $t("labels.on")
            }}</span>
          </template>
          <div>{{ $t("tagging.automatic_reprocessing_tt") }}</div>
        </v-tooltip>
      </td>
    </tr>
    <tr v-if="showFileName">
      <th>{{ $t("labels.source_file") }}</th>
      <td class="text-right">
        <v-tooltip location="bottom" max-width="600px">
          <template #activator="{ props }">
            <a
              :href="taggingBatch.source_file"
              v-if="taggingBatch.source_file"
              target="_blank"
              v-bind="props"
            >
              <v-icon size="small" color="secondary">fa fa-download</v-icon>
            </a>
          </template>
          {{ sourceFileName }}
        </v-tooltip>
      </td>
    </tr>
    <tr v-if="showFileName && taggingBatch.annotated_file">
      <th>
        <v-tooltip location="bottom" max-width="600px">
          <template #activator="{ props }">
            <span v-bind="props">
              {{ $t("tagging.annotated_source_file") }}
              <v-icon size="small">fa fa-info-circle</v-icon>
            </span>
          </template>
          {{ $t("tagging.annotated_source_file_tt") }}
        </v-tooltip>
      </th>
      <td class="text-right">
        <!-- the key bellow is there to prevent the tooltip from disappearing
        on change, probably due to some bug in vuetify -->
        <v-tooltip
          location="bottom"
          max-width="600px"
          v-if="showFileName && taggingBatch.annotated_file"
          :key="'tt' + taggingBatch.state"
        >
          <template #activator="{ props }">
            <a
              :href="taggingBatch.annotated_file"
              target="_blank"
              v-bind="props"
            >
              <v-icon size="small" color="secondary">fa fa-download</v-icon>
            </a>
          </template>
          {{ annotatedFileName }}
        </v-tooltip>
      </td>
    </tr>
    <tr v-if="taggingBatch.import_count > 1">
      <th>
        <v-tooltip location="bottom">
          <template #activator="{ props }">
            <span v-bind="props">
              {{ $t("tagging.import_count") }}
              <v-icon size="small">fa fa-info-circle</v-icon>
            </span>
          </template>
          {{ $t("tagging.import_count_tt") }}
        </v-tooltip>
      </th>
      <td class="text-right">
        <a @click="showAttemptDialog = true">
          <v-icon size="small" color="secondary"
            >fa fa-external-link-alt</v-icon
          >
          {{ taggingBatch.import_count }}
        </a>
      </td>
    </tr>
    <!-- stats -->
    <!-- total row count -->
    <tr v-if="data">
      <th class="pt-6">
        <v-tooltip location="bottom">
          <template #activator="{ props }">
            <span v-bind="props">{{ $t("tagging.data_rows") }}</span>
          </template>
          {{ $t("tagging.data_rows_tt") }}
        </v-tooltip>
      </th>
      <td class="text-right pt-6">
        <v-tooltip location="bottom">
          <template #activator="{ props }">
            <span v-bind="props">{{ data.rows_total }}</span>
          </template>
          {{ $t("tagging.data_rows_tt") }}
        </v-tooltip>
      </td>
    </tr>
    <tr v-if="data">
      <th>
        <v-tooltip location="bottom">
          <template #activator="{ props }">
            <span v-bind="props">{{ $t("tagging.matched_rows") }}</span>
          </template>
          {{ $t("tagging.matched_rows_tt") }}
        </v-tooltip>
      </th>
      <td class="text-right">
        <v-tooltip location="bottom">
          <template #activator="{ props }">
            <span v-bind="props">{{
              data.rows_total - data.rows_no_match
            }}</span>
          </template>
          {{ $t("tagging.matched_rows_tt") }}
        </v-tooltip>
      </td>
      <td class="progress_column">
        <v-progress-linear
          :model-value="
            data.rows_total > 0
              ? ((data.rows_total - data.rows_no_match) / data.rows_total) * 100
              : 0
          "
          color="success"
          height="20"
          rounded
        >
          <template #default="{ value }">
            <strong class="text-white text-caption"
              >{{ Math.round(10 * value) / 10 }} %</strong
            >
          </template>
        </v-progress-linear>
      </td>
    </tr>
    <!-- unmatched row count -->
    <tr v-if="data">
      <th>
        <v-tooltip location="bottom">
          <template #activator="{ props }">
            <span v-bind="props">
              {{ $t("tagging.no_match_rows") }}
            </span>
          </template>
          {{ $t("tagging.no_match_rows_tt") }}
        </v-tooltip>
      </th>
      <td class="text-right">
        <v-tooltip location="bottom">
          <template #activator="{ props }">
            <span v-bind="props">{{ data.rows_no_match }}</span>
          </template>
          {{ $t("tagging.no_match_rows_tt") }}
        </v-tooltip>
      </td>
      <td class="progress_column">
        <v-progress-linear
          :model-value="
            data.rows_total > 0
              ? (data.rows_no_match / data.rows_total) * 100
              : 0
          "
          color="error"
          height="20"
          rounded
        >
          <template #default="{ value }">
            <strong class="text-white text-caption"
              >{{ Math.round(10 * value) / 10 }} %</strong
            >
          </template>
        </v-progress-linear>
      </td>
    </tr>
    <!-- matched titles count -->
    <tr v-if="data">
      <th :class="finished ? 'pt-4' : ''">
        <v-tooltip location="bottom">
          <template #activator="{ props }">
            <span v-bind="props">{{ $t("tagging.matched_celus_titles") }}</span>
          </template>
          <div>{{ $t("tagging.matched_titles_tt") }}</div>
          <div>{{ $t("tagging.title_number_note") }}</div>
        </v-tooltip>
      </th>
      <td class="text-right" :class="finished ? 'pt-4' : ''">
        <v-tooltip location="bottom">
          <template #activator="{ props }">
            <span v-bind="props">{{ data.unique_matched_titles }}</span>
          </template>
          <div>{{ $t("tagging.matched_titles_tt") }}</div>
          <div>{{ $t("tagging.title_number_note") }}</div>
        </v-tooltip>
      </td>
    </tr>
    <!-- already tagged titles count -->
    <tr v-if="finished && data && data.already_tagged_titles">
      <th class="pl-3 font-weight-light">
        <v-tooltip location="bottom">
          <template #activator="{ props }">
            <span v-bind="props">{{
              $t("tagging.already_tagged_celus_titles")
            }}</span>
          </template>
          <div>{{ $t("tagging.already_tagged_titles_tt") }}</div>
        </v-tooltip>
      </th>
      <td class="text-right">
        <v-tooltip location="bottom">
          <template #activator="{ props }">
            <span v-bind="props">{{ data.already_tagged_titles }}</span>
          </template>
          <div>{{ $t("tagging.already_tagged_titles_tt") }}</div>
        </v-tooltip>
      </td>
    </tr>
    <!-- titles with a clashing exclusive tag -->
    <tr v-if="finished && data && data.exclusively_tagged_titles">
      <th class="pl-3 font-weight-light">
        <v-tooltip location="bottom">
          <template #activator="{ props }">
            <span v-bind="props">{{
              $t("tagging.exclusively_tagged_celus_titles")
            }}</span>
          </template>
          <div>{{ $t("tagging.exclusively_tagged_titles_tt") }}</div>
        </v-tooltip>
      </th>
      <td class="text-right">
        <v-tooltip location="bottom">
          <template #activator="{ props }">
            <span v-bind="props">{{ data.exclusively_tagged_titles }}</span>
          </template>
          <div>{{ $t("tagging.exclusively_tagged_titles_tt") }}</div>
        </v-tooltip>
      </td>
    </tr>
    <!-- tagged titles count -->
    <tr v-if="finished && data">
      <th>
        <v-tooltip location="bottom">
          <template #activator="{ props }">
            <span v-bind="props">{{
              data.tagged_titles !== data.unique_matched_titles
                ? $t("tagging.actually_tagged_celus_titles")
                : $t("tagging.tagged_celus_titles")
            }}</span>
          </template>
          <div>{{ $t("tagging.tagged_titles_tt") }}</div>
          <div>{{ $t("tagging.tagged_titles_note") }}</div>
        </v-tooltip>
      </th>
      <td class="text-right">
        <v-tooltip location="bottom">
          <template #activator="{ props }">
            <span v-bind="props">{{ data.tagged_titles }}</span>
          </template>
          <div>{{ $t("tagging.tagged_titles_tt") }}</div>
          <div>{{ $t("tagging.tagged_titles_note") }}</div>
        </v-tooltip>
      </td>
    </tr>
    <!-- recognized columns -->
    <tr v-if="!finished && data">
      <th>
        <v-tooltip location="bottom">
          <template #activator="{ props }">
            <span v-bind="props">
              {{ $t("tagging.recognized_columns") }}
            </span>
          </template>
          {{ $t("tagging.recognized_columns_tt") }}
        </v-tooltip>
      </th>
      <td class="text-right">
        <v-tooltip
          location="bottom"
          v-if="taggingBatch.preflight.recognized_columns.length"
        >
          <template #activator="{ props }">
            <span v-bind="props">
              <v-chip
                v-for="col in taggingBatch.preflight.recognized_columns"
                :key="col"
                label
                class="ml-2"
                size="small"
                >{{ col }}
              </v-chip>
            </span>
          </template>
          {{ $t("tagging.recognized_columns_tt") }}
        </v-tooltip>
        <span v-else>
          <v-icon color="warning" size="small"
            >fa fa-exclamation-triangle</v-icon
          >
          {{ $t("tagging.no_recognized_columns") }}
        </span>
      </td>
    </tr>
    <!-- explicit tags stats -->
    <tr v-if="data && !isEmpty(data.tag_stats)">
      <th>{{ $t("tagging.tag_stats") }}</th>
      <td class="text-right">
        <v-tooltip
          v-for="(rec, name) in data.tag_stats"
          :key="name"
          location="bottom"
          max-width="600px"
        >
          <template #activator="{ props }">
            <v-chip
              class="ml-1"
              :color="rec.used > 0 ? 'success' : 'disabled'"
              v-bind="props"
              size="small"
            >
              <ShortenText :text="name" :length="30"> </ShortenText>
            </v-chip>
          </template>
          {{ $t("tag_stats_tt", rec) }}
        </v-tooltip>
      </td>
    </tr>
    <tr
      v-if="
        taggingBatch.state === 'prefailed' || taggingBatch.state === 'failed'
      "
    >
      <th>{{ $t("labels.error") }}</th>
      <td class="text-right">
        <v-icon size="small" color="error">fa fa-exclamation-circle</v-icon>
        <ShortenText
          :text="taggingBatch.preflight.error || taggingBatch.postflight.error"
        >
        </ShortenText>
      </td>
    </tr>
    <v-dialog
      v-model="showAttemptDialog"
      v-if="showAttemptDialog"
      max-width="720px"
    >
      <v-card>
        <v-card-title>{{ $t("tagging.imports") }}</v-card-title>
        <v-card-text>
          <TaggingAttemptList
            :tagging-batch="taggingBatch"
          ></TaggingAttemptList>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="showAttemptDialog = false" class="mx-1 my-2">
            {{ $t("actions.close") }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </table>
</template>

<script>
import ShortenText from "@/components/ShortenText";
import TaggingAttemptList from "@/components/tagging-batches/TaggingAttemptList.vue";
import TaggingBatchStateWidget from "@/components/tagging-batches/TaggingBatchStateWidget.vue";
import TagChip from "@/components/tags/TagChip";
import isEmpty from "lodash/isEmpty";
export default {
  name: "TaggingBatchStats",

  components: {
    ShortenText,
    TaggingAttemptList,
    TagChip,
    TaggingBatchStateWidget,
  },

  props: {
    taggingBatch: { type: Object, required: true },
    showFileName: { type: Boolean, default: false },
    fullWidth: { type: Boolean, default: false },
    showAttempts: { type: Boolean, default: false },
  },

  data() {
    return {
      showAttemptDialog: false,
    };
  },

  computed: {
    finished() {
      return this.taggingBatch?.state === "imported";
    },
    data() {
      if (this.finished) {
        return this.taggingBatch?.postflight;
      }
      return this.taggingBatch?.preflight;
    },
    sourceFileName() {
      return this.pathToFname(this.taggingBatch.source_file);
    },
    annotatedFileName() {
      return this.pathToFname(this.taggingBatch.annotated_file);
    },
  },

  methods: {
    isEmpty,
    pathToFname(path) {
      if (path) {
        const url = new URL(path);
        const parts = url.pathname.split("/");
        return parts[parts.length - 1];
      }
      return "";
    },
  },
};
</script>

<style lang="scss" scoped>
tr {
  min-height: 25px;
  height: 25px;
}

th {
  min-width: 230px;
}

.progress_column {
  padding-left: 10px;
  width: 100px;
  :deep(.v-progress-linear__background) {
    opacity: 0.4 !important;
  }
}
</style>
