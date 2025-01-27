<i18n lang="yaml">
en:
  tag_stats_tt: "Matched rows: {matched_lines}, matched titles: {matched_titles}"

cs:
  tag_stats_tt: "Odpovídajících řádků: {found}, nalezených titulů: {used}"
</i18n>
<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<template>
  <table class="overview" :class="{ 'full-width': fullWidth }">
    <tr>
      <th>{{ $t("labels.state") }}</th>
      <td class="text-right">
        <TaggingBatchStateWidget :batch="taggingBatch" />
      </td>
    </tr>

    <tr v-if="taggingBatch.tag">
      <th>{{ $t("labels.tag") }}</th>
      <td class="text-right">
        <TagChip :tag="taggingBatch.tag" show-class />
      </td>
    </tr>
    <tr v-else-if="taggingBatch.tag_class">
      <th>{{ $t("labels.tag_class") }}</th>
      <td class="text-right">
        <TagChip :tag="taggingBatch.tag_class" />
      </td>
    </tr>

    <tr v-if="taggingBatch.state === 'imported'">
      <th>{{ $t("tagging.automatic_reprocessing") }}</th>
      <td class="text-right">
        <!-- the key bellow is there to prevent the tooltip from disappearing
        on change, probably due to some bug in vuetify -->
        <v-tooltip
          bottom
          max-width="600px"
          :key="'tt' + taggingBatch.reprocess_after"
        >
          <template #activator="{ on }">
            <span v-on="on">{{
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
        <v-tooltip bottom max-width="600px">
          <template #activator="{ on }">
            <a
              :href="taggingBatch.source_file"
              v-if="taggingBatch.source_file"
              target="_blank"
              v-on="on"
            >
              <v-icon small color="secondary">fa fa-download</v-icon>
            </a>
          </template>
          {{ sourceFileName }}
        </v-tooltip>
      </td>
    </tr>
    <tr v-if="showFileName && taggingBatch.annotated_file">
      <th>
        <v-tooltip bottom max-width="600px">
          <template #activator="{ on }">
            <span v-on="on">
              {{ $t("tagging.annotated_source_file") }}
              <v-icon small>fa fa-info-circle</v-icon>
            </span>
          </template>
          {{ $t("tagging.annotated_source_file_tt") }}
        </v-tooltip>
      </th>
      <td class="text-right">
        <!-- the key bellow is there to prevent the tooltip from disappearing
        on change, probably due to some bug in vuetify -->
        <v-tooltip
          bottom
          max-width="600px"
          v-if="showFileName && taggingBatch.annotated_file"
          :key="'tt' + taggingBatch.state"
        >
          <template #activator="{ on }">
            <a :href="taggingBatch.annotated_file" target="_blank" v-on="on">
              <v-icon small color="secondary">fa fa-download</v-icon>
            </a>
          </template>
          {{ annotatedFileName }}
        </v-tooltip>
      </td>
    </tr>

    <tr v-if="taggingBatch.import_count > 1">
      <th>
        <v-tooltip bottom>
          <template #activator="{ on }">
            <span v-on="on">
              {{ $t("tagging.import_count") }}
              <v-icon small>fa fa-info-circle</v-icon>
            </span>
          </template>
          {{ $t("tagging.import_count_tt") }}
        </v-tooltip>
      </th>
      <td class="text-right">
        <a @click="showAttemptDialog = true">
          <v-icon small color="secondary">fa fa-external-link-alt</v-icon>
          {{ taggingBatch.import_count }}
        </a>
      </td>
    </tr>

    <!-- stats -->
    <!-- total row count -->
    <tr v-if="data">
      <th class="pt-6">
        <v-tooltip bottom>
          <template #activator="{ on }">
            <span v-on="on">{{ $t("tagging.data_rows") }}</span>
          </template>
          {{ $t("tagging.data_rows_tt") }}
        </v-tooltip>
      </th>
      <td class="text-right pt-6">
        <v-tooltip bottom>
          <template #activator="{ on }">
            <span v-on="on">{{ data.rows_total }}</span>
          </template>
          {{ $t("tagging.data_rows_tt") }}
        </v-tooltip>
      </td>
    </tr>

    <!-- unmatched row count -->
    <tr v-if="data">
      <th>
        <v-tooltip bottom>
          <template #activator="{ on }">
            <span v-on="on">
              {{ $t("tagging.no_match_rows") }}
            </span>
          </template>
          {{ $t("tagging.no_match_rows_tt") }}
        </v-tooltip>
      </th>
      <td class="text-right">
        <v-tooltip bottom>
          <template #activator="{ on }">
            <span v-on="on">{{ data.rows_no_match }}</span>
          </template>
          {{ $t("tagging.no_match_rows_tt") }}
        </v-tooltip>
      </td>
    </tr>

    <!-- matched titles count -->
    <tr v-if="data">
      <th :class="finished ? 'pt-4' : ''">
        <v-tooltip bottom>
          <template #activator="{ on }">
            <span v-on="on">{{ $t("tagging.matched_titles") }}</span>
          </template>
          <div>{{ $t("tagging.matched_titles_tt") }}</div>
          <div>{{ $t("tagging.title_number_note") }}</div>
        </v-tooltip>
      </th>
      <td class="text-right" :class="finished ? 'pt-4' : ''">
        <v-tooltip bottom>
          <template #activator="{ on }">
            <span v-on="on">{{ data.unique_matched_titles }}</span>
          </template>
          <div>{{ $t("tagging.matched_titles_tt") }}</div>
          <div>{{ $t("tagging.title_number_note") }}</div>
        </v-tooltip>
      </td>
    </tr>

    <!-- already tagged titles count -->
    <tr v-if="finished && data && data.already_tagged_titles">
      <th class="pl-3 font-weight-light">
        <v-tooltip bottom>
          <template #activator="{ on }">
            <span v-on="on">{{ $t("tagging.already_tagged_titles") }}</span>
          </template>
          <div>{{ $t("tagging.already_tagged_titles_tt") }}</div>
        </v-tooltip>
      </th>
      <td class="text-right">
        <v-tooltip bottom>
          <template #activator="{ on }">
            <span v-on="on">{{ data.already_tagged_titles }}</span>
          </template>
          <div>{{ $t("tagging.already_tagged_titles_tt") }}</div>
        </v-tooltip>
      </td>
    </tr>

    <!-- titles with a clashing exclusive tag -->
    <tr v-if="finished && data && data.exclusively_tagged_titles">
      <th class="pl-3 font-weight-light">
        <v-tooltip bottom>
          <template #activator="{ on }">
            <span v-on="on">{{ $t("tagging.exclusively_tagged_titles") }}</span>
          </template>
          <div>{{ $t("tagging.exclusively_tagged_titles_tt") }}</div>
        </v-tooltip>
      </th>
      <td class="text-right">
        <v-tooltip bottom>
          <template #activator="{ on }">
            <span v-on="on">{{ data.exclusively_tagged_titles }}</span>
          </template>
          <div>{{ $t("tagging.exclusively_tagged_titles_tt") }}</div>
        </v-tooltip>
      </td>
    </tr>

    <!-- tagged titles count -->
    <tr v-if="finished && data">
      <th>
        <v-tooltip bottom>
          <template #activator="{ on }">
            <span v-on="on">{{
              data.tagged_titles !== data.unique_matched_titles
                ? $t("tagging.actually_tagged_titles")
                : $t("tagging.tagged_titles")
            }}</span>
          </template>
          <div>{{ $t("tagging.tagged_titles_tt") }}</div>
          <div>{{ $t("tagging.tagged_titles_note") }}</div>
        </v-tooltip>
      </th>
      <td class="text-right">
        <v-tooltip bottom>
          <template #activator="{ on }">
            <span v-on="on">{{ data.tagged_titles }}</span>
          </template>
          <div>{{ $t("tagging.tagged_titles_tt") }}</div>
          <div>{{ $t("tagging.tagged_titles_note") }}</div>
        </v-tooltip>
      </td>
    </tr>

    <!-- recognized columns -->
    <tr v-if="!finished && data">
      <th>
        <v-tooltip bottom>
          <template #activator="{ on }">
            <span v-on="on">
              {{ $t("tagging.recognized_columns") }}
            </span>
          </template>
          {{ $t("tagging.recognized_columns_tt") }}
        </v-tooltip>
      </th>
      <td class="text-right">
        <v-tooltip
          bottom
          v-if="taggingBatch.preflight.recognized_columns.length"
        >
          <template #activator="{ on }">
            <span v-on="on">
              <v-chip
                v-for="col in taggingBatch.preflight.recognized_columns"
                :key="col"
                label
                class="ml-2"
                small
                >{{ col }}
              </v-chip>
            </span>
          </template>
          {{ $t("tagging.recognized_columns_tt") }}
        </v-tooltip>
        <span v-else>
          <v-icon color="warning" small>fa-exclamation-triangle</v-icon>
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
          bottom
          max-width="600px"
        >
          <template #activator="{ on }">
            <v-chip
              class="ml-1"
              :color="rec.used > 0 ? 'success' : 'disabled'"
              v-on="on"
              small
            >
              {{ name }}
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
      <td>
        <v-icon small color="error">fa-exclamation-circle</v-icon>
        {{ taggingBatch.preflight.error || taggingBatch.postflight.error }}
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
          <TaggingAttemptList :tagging-batch="taggingBatch" />
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
import TagChip from "@/components/tags/TagChip";
import TaggingBatchStateWidget from "@/components/tagging-batches/TaggingBatchStateWidget.vue";
import isEmpty from "lodash/isEmpty";
import TaggingAttemptList from "@/components/tagging-batches/TaggingAttemptList.vue";
export default {
  name: "TaggingBatchStats",

  components: { TaggingAttemptList, TagChip, TaggingBatchStateWidget },

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
