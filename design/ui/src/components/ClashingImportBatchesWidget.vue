<i18n lang="yaml">
en:
  clashing_import_batches:
    title: Clashing Imports
    header:
      record_count: Records
      created: Created
      month: Month
      user: User
      sushi: Sushi
    tooltip:
      manual: Manually uploaded
      sushi: Harvested using sushi

cs:
  clashing_import_batches:
    title: Konfliktní importy
    header:
      record_count: Záznamů
      created: Vytvořeno
      month: Měsíc
      user: Uživatel
      sushi: Sushi
    tooltip:
      manual: Ručně nahráno
      sushi: Staženo přes sushi
</i18n>

<template>
  <v-container>
    <h3>{{ $t("clashing_import_batches.title") }}</h3>
    <v-data-table
      :headers="headers"
      :items="importBatches"
      :footer-props="{
        disableItemsPerPage: true,
      }"
      dense
      hide-default-footer
    >
      <template #item.created="{ item }">
        <span v-html="isoDateTimeFormatSpans(item.created)"></span>
      </template>
      <template #item.date="{ item }">
        <span v-html="ymDateFormat(parseDateTime(item.date))"></span>
      </template>
      <template #item.sushifetchattempt="{ item }">
        <CheckMark
          :value="!!item.sushifetchattempt"
          :true-tooltip="$t('clashing_import_batches.tooltip.sushi')"
          :false-tooltip="$t('clashing_import_batches.tooltip.manual')"
        />
      </template>
    </v-data-table>
  </v-container>
</template>

<script>
import {
  isoDateTimeFormatSpans,
  ymDateFormat,
  parseDateTime,
} from "../libs/dates";
import CheckMark from "@/components/util/CheckMark";

export default {
  name: "ClashingImportBatchesWidget",

  components: {
    CheckMark,
  },

  props: {
    importBatches: {
      required: true,
    },
  },

  computed: {
    headers() {
      return [
        {
          text: this.$i18n.t("clashing_import_batches.header.created"),
          value: "created",
        },
        {
          text: this.$i18n.t("clashing_import_batches.header.month"),
          value: "date",
        },
        {
          text: this.$i18n.t("clashing_import_batches.header.user"),
          value: "user.email",
        },
        {
          text: this.$i18n.t("clashing_import_batches.header.sushi"),
          value: "sushifetchattempt",
        },
        {
          text: this.$i18n.t("clashing_import_batches.header.record_count"),
          value: "accesslog_count",
        },
        // TODO sushi indicator
      ];
    },
  },
  methods: {
    isoDateTimeFormatSpans: isoDateTimeFormatSpans,
    ymDateFormat: ymDateFormat,
    parseDateTime: parseDateTime,
  },
};
</script>

<style lang="scss">
span.time {
  font-weight: 300;
  font-size: 87.5%;
}
</style>
