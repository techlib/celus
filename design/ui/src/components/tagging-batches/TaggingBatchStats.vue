<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<template>
  <table class="overview" :class="{ 'full-width': fullWidth }">
    <tr>
      <th>{{ $t("labels.state") }}</th>
      <td class="text-right">
        <TaggingBatchStateIcon :batch="taggingBatch" />
        {{ $t("tag_state." + taggingBatch.state) }}
      </td>
    </tr>
    <tr v-if="taggingBatch.tag">
      <th>{{ $t("labels.tag") }}</th>
      <td class="text-right">
        <TagChip :tag="taggingBatch.tag" show-class />
      </td>
    </tr>
    <tr v-if="showFileName">
      <th>{{ $t("labels.source_file") }}</th>
      <td class="text-right">
        <a
          :href="taggingBatch.source_file"
          v-if="taggingBatch.source_file"
          target="_blank"
          >{{ sourceFileName }}</a
        >
      </td>
    </tr>
    <tr v-if="showFileName && taggingBatch.annotated_file">
      <th>
        <v-tooltip bottom>
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
        <a
          :href="taggingBatch.annotated_file"
          v-if="taggingBatch.annotated_file"
          target="_blank"
          >{{ annotatedFileName }}</a
        >
      </td>
    </tr>

    <!-- stats -->
    <!-- total row count -->
    <tr v-if="stats">
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
            <span v-on="on">{{ stats.row_count }}</span>
          </template>
          {{ $t("tagging.data_rows_tt") }}
        </v-tooltip>
      </td>
    </tr>
    <!-- unmatched row count -->
    <tr v-if="stats">
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
            <span v-on="on">{{ stats.no_match }}</span>
          </template>
          {{ $t("tagging.no_match_rows_tt") }}
        </v-tooltip>
      </td>
    </tr>

    <!-- matched titles count -->
    <tr v-if="stats">
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
            <span v-on="on">{{ stats.unique_matched_titles }}</span>
          </template>
          <div>{{ $t("tagging.matched_titles_tt") }}</div>
          <div>{{ $t("tagging.title_number_note") }}</div>
        </v-tooltip>
      </td>
    </tr>

    <!-- already tagged titles count -->
    <tr v-if="finished && stats && stats.already_tagged_titles">
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
            <span v-on="on">{{ stats.already_tagged_titles }}</span>
          </template>
          <div>{{ $t("tagging.already_tagged_titles_tt") }}</div>
        </v-tooltip>
      </td>
    </tr>

    <!-- titles with a clashing exclusive tag -->
    <tr v-if="finished && stats && stats.exclusively_tagged_titles">
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
            <span v-on="on">{{ stats.exclusively_tagged_titles }}</span>
          </template>
          <div>{{ $t("tagging.exclusively_tagged_titles_tt") }}</div>
        </v-tooltip>
      </td>
    </tr>

    <!-- tagged titles count -->
    <tr v-if="finished && stats">
      <th>
        <v-tooltip bottom>
          <template #activator="{ on }">
            <span v-on="on">{{
              stats.tagged_titles !== stats.unique_matched_titles
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
            <span v-on="on">{{ stats.tagged_titles }}</span>
          </template>
          <div>{{ $t("tagging.tagged_titles_tt") }}</div>
          <div>{{ $t("tagging.tagged_titles_note") }}</div>
        </v-tooltip>
      </td>
    </tr>

    <!-- recognized columns -->
    <tr v-if="!finished && stats">
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
        <v-tooltip bottom>
          <template #activator="{ on }">
            <span v-on="on">
              <v-chip
                v-for="col in taggingBatch.preflight.recognized_columns"
                :key="col"
                label
                class="ml-2"
                >{{ col }}
              </v-chip>
            </span>
          </template>
          {{ $t("tagging.recognized_columns_tt") }}
        </v-tooltip>
      </td>
    </tr>
    <tr
      v-if="
        taggingBatch.state === 'prefailed' || taggingBatch.state === 'failed'
      "
    >
      <th>{{ $t("labels.error") }}</th>
      <td>{{ taggingBatch.preflight.error }}</td>
    </tr>
  </table>
</template>
<script>
import TaggingBatchStateIcon from "@/components/tagging-batches/TaggingBatchStateIcon";
import TagChip from "@/components/tags/TagChip";
export default {
  name: "TaggingBatchStats",
  components: { TagChip, TaggingBatchStateIcon },
  props: {
    taggingBatch: { type: Object, required: true },
    showFileName: { type: Boolean, default: false },
    fullWidth: { type: Boolean, default: false },
  },

  computed: {
    finished() {
      return this.taggingBatch?.state === "imported";
    },
    stats() {
      if (this.finished) {
        return this.taggingBatch?.postflight?.stats;
      }
      return this.taggingBatch?.preflight?.stats;
    },
    sourceFileName() {
      return this.pathToFname(this.taggingBatch.source_file);
    },
    annotatedFileName() {
      return this.pathToFname(this.taggingBatch.annotated_file);
    },
  },

  methods: {
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
