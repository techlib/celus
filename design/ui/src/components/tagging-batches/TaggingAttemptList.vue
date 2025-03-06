<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<template>
  <v-data-table
    :items="attempts"
    item-key="pk"
    :headers="headers"
    :loading="loading"
  >
    <template #[`item.created`]="{ item }">
      <span v-html="formatDate(item.created)"></span>
    </template>
    <template #[`item.unique_matched_titles`]="{ item }">
      <span v-html="formatInteger(item.unique_matched_titles)"></span>
    </template>
    <template #[`item.tagged_titles`]="{ item }">
      <span v-html="formatInteger(item.tagged_titles)"></span>
    </template>
    <template #[`item.already_tagged_titles`]="{ item }">
      <span v-html="formatInteger(item.already_tagged_titles)"></span>
    </template>
  </v-data-table>
</template>

<script>
import cancellation from "@/mixins/cancellation";
import { isoDateTimeFormatSpans, parseDateTime } from "@/libs/dates";
import { formatInteger } from "@/libs/numbers";

export default {
  name: "TaggingAttemptList",

  mixins: [cancellation],

  props: {
    taggingBatch: { type: Object, required: true },
  },

  data() {
    return {
      attempts: [],
      loading: false,
    };
  },

  computed: {
    headers() {
      return [
        {
          title: this.$i18n.t("labels.created"),
          value: "created",
        },
        {
          title: this.$i18n.t("tagging.matched_titles"),
          value: "unique_matched_titles",
          align: "end",
        },
        {
          title: this.$i18n.t("tagging.tagged_titles"),
          value: "tagged_titles",
          align: "end",
        },
        {
          title: this.$i18n.t("tagging.already_tagged_titles"),
          value: "already_tagged_titles",
          align: "end",
        },
      ];
    },
  },

  methods: {
    formatInteger,
    formatDate(date) {
      return isoDateTimeFormatSpans(parseDateTime(date));
    },
    async fetchAttempts() {
      this.loading = true;
      let reply = await this.http({
        method: "get",
        url: `/api/tags/tagging-batch/${this.taggingBatch.pk}/imports/`,
      });
      if (!reply.error) {
        this.attempts = reply.response.data;
      }
      this.loading = false;
    },
  },

  mounted() {
    this.fetchAttempts();
  },
};
</script>

<style scoped lang="scss"></style>
