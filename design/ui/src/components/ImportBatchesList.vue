<i18n lang="yaml">
en:
  import_batches_list:
    header:
      record_count: Records
      created: Created
      month: Month
      user: User
      organization: Organization
      source: Source
      report_type: Report type
    tooltip:
      manual: Manually uploaded
      sushi: Harvested using SUSHI

cs:
  import_batches_list:
    header:
      record_count: Záznamů
      created: Vytvořeno
      month: Měsíc
      user: Uživatel
      organization: Organizace
      source: Zdroj
      report_type: Typ reportu
    tooltip:
      manual: Ručně nahráno
      sushi: Staženo přes SUSHI
</i18n>

<template>
  <v-container>
    <h3 v-if="titleText">{{ titleText || $t("import_batches_list.title") }}</h3>
    <v-data-table
      :headers="headers"
      :items="importBatches"
      :footer-props="{
        disableItemsPerPage: true,
      }"
      dense
      :loading="loading"
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
          true-icon="fas fa-cloud-download-alt"
          false-icon="fas fa-upload"
          true-color="primary"
          false-color="primary"
          :true-tooltip="$t('import_batches_list.tooltip.sushi')"
          :false-tooltip="$t('import_batches_list.tooltip.manual')"
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
  name: "ImportBatchesList",

  components: {
    CheckMark,
  },

  props: {
    importBatches: {
      required: true,
    },
    titleText: {
      required: false,
      type: String,
    },
    loading: {
      required: false,
      type: Boolean,
      default: false,
    },
  },

  computed: {
    headers() {
      return [
        {
          text: this.$i18n.t("import_batches_list.header.created"),
          value: "created",
        },
        {
          text: this.$i18n.t("import_batches_list.header.month"),
          value: "date",
        },
        {
          text: this.$i18n.t("import_batches_list.header.report_type"),
          value: "report_type.short_name",
        },
        {
          text: this.$i18n.t("import_batches_list.header.user"),
          value: "user.email",
        },
        {
          text: this.$i18n.t("import_batches_list.header.organization"),
          value: "organization.short_name",
        },
        {
          text: this.$i18n.t("import_batches_list.header.source"),
          value: "sushifetchattempt",
        },
        {
          text: this.$i18n.t("import_batches_list.header.record_count"),
          value: "accesslog_count",
        },
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
