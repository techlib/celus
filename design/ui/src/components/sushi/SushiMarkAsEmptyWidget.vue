<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml">
en:
  mark_as_empty_confirmation_text: Are you sure you want to mark the selected record as empty data?|Are you sure you want to mark the selected {count} records as empty data?
  mark_as_empty_description1: Such records will be considered successfully processed, but without any data.
  mark_as_empty_description2: No further attempts to harvest the data will be made.
  mark_as_empty_description3: In data coverage calculations, such months will be considered covered.
  mark_as_empty_title: "Mark as empty data"
  processing: "Processing"
  finished: All records have been processed.
  errors: "{count} error occurred.|{count} errors occurred."
cs:
  mark_as_empty_confirmation_text: Opravdu chcete označit vybraný záznam jako prázdná data?|Opravdu chcete označit {count} vybrané záznamy jako prázdná data?|Opravdu chcete označit {count} vybraných záznamů jako prázdná data?
  mark_as_empty_description1: Takové záznamy budou považovány za úspěšně zpracované, ale bez jakýchkoli dat.
  mark_as_empty_description2: Nebudou podnikány žádné další pokusy o stahování dat.
  mark_as_empty_description3: Při výpočtech pokrytí dat budou takové měsíce považovány za pokryté.
  mark_as_empty_title: Označit jako prázdná data
  processing: Zpracovávám
  finished: Všechny záznamy byly zpracovány.
  errors: "V průběhu se vyskytla {count} chyba.|V průběhu se vyskytly {count} chyby.|V průběhu se vyskytlo {count} chyb."
</i18n>

<template>
  <v-card>
    <v-card-title>{{ $t("mark_as_empty_title") }}</v-card-title>
    <v-card-text>
      <v-row>
        <v-col v-if="!processing">
          <p>
            {{ $tc("mark_as_empty_confirmation_text", totalCount) }}
          </p>
          <ul>
            <li>{{ $t("mark_as_empty_description1") }}</li>
            <li>{{ $t("mark_as_empty_description2") }}</li>
            <li>{{ $t("mark_as_empty_description3") }}</li>
          </ul>
        </v-col>
        <v-col v-else>
          <span>{{ $t("processing") }}:</span>
          <v-progress-linear :value="progress" height="30">
            <span>{{ processedCount }} / {{ totalCount }}</span>
          </v-progress-linear>
        </v-col>
      </v-row>
    </v-card-text>
    <v-card-actions>
      <v-spacer />
      <v-btn @click="$emit('cancel')" class="mr-2">{{
        $t("actions.cancel")
      }}</v-btn>
      <v-btn @click="markAsEmpty" color="primary">{{
        $t("actions.proceed")
      }}</v-btn>
    </v-card-actions>
  </v-card>
</template>

<script>
import cancellation from "@/mixins/cancellation";
import { mapActions } from "vuex";
export default {
  name: "SushiMarkAsEmptyWidget",

  mixins: [cancellation],

  props: {
    records: {
      type: Array,
      required: true,
    },
  },

  data() {
    return {
      processing: false,
      processedCount: 0,
      errorCount: 0,
    };
  },

  computed: {
    totalCount() {
      return this.records.length;
    },
    progress() {
      return (100 * this.processedCount) / this.totalCount;
    },
  },

  methods: {
    ...mapActions(["showSnackbar"]),
    async markAsEmpty() {
      this.processing = true;
      for (let record of this.records) {
        await this.processRecord(record);
      }
      this.processing = false;
      let message = this.$t("finished");
      let color = "success";
      if (this.errorCount) {
        message += " " + this.$tc("errors", this.errorCount);
        color = "warning";
      }
      await this.showSnackbar({ content: message, color });
      this.$emit("finished");
    },
    async processRecord({ organization, platform, report_type, start_date }) {
      let reply = await this.http({
        url: "/api/import-batch/create-empty/",
        method: "post",
        data: {
          organization,
          platform,
          report_type,
          date: start_date,
        },
        dontShowError: true,
      });
      this.processedCount++;
      if (reply.error) {
        this.errorCount++;
      }
    },
  },
};
</script>

<style scoped lang="scss"></style>
