<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<template>
  <div class="pt-2">
    <v-card v-if="usedOrganization" class="mb-6">
      <v-card-text>
        <table class="overview">
          <tr>
            <th>{{ $t("labels.organization") }}</th>
            <td>{{ usedOrganization.name }}</td>
          </tr>
          <tr>
            <th>{{ $t("title_fields.start_date") }}</th>
            <td>{{ usedStartDate }}</td>
          </tr>
          <tr>
            <th>{{ $t("title_fields.end_date") }}</th>
            <td>{{ usedEndDate }}</td>
          </tr>
        </table>
      </v-card-text>
    </v-card>
    <v-expansion-panels>
      <SpecializedReportPart
        v-for="(definition, index) in parts"
        :key="index"
        :name="definition.name"
        :description="definition.description"
        :explanation="definition.explanation"
        :stages="definition.stages"
        :data="resultData[definition.name] ? resultData[definition.name] : {}"
        :loading="loading"
        :reportDataSources="sourceReportsObj"
        :implementationNote="definition.implementationNote"
      ></SpecializedReportPart>
    </v-expansion-panels>
  </div>
</template>

<script>
import cancellation from "@/mixins/cancellation";
import SpecializedReportPart from "@/components/special/SpecializedReportPart";
import { mapGetters } from "vuex";

export default {
  name: "SpecializedReport",

  mixins: [cancellation],

  components: { SpecializedReportPart },

  props: {
    definition: { required: true, type: Object },
  },

  data() {
    return {
      resultData: [],
      loading: false,
      usedOrganization: null,
      usedStartDate: null,
      usedEndDate: null,
    };
  },

  computed: {
    ...mapGetters({
      dateRangeStart: "dateRangeStartText",
      dateRangeEnd: "dateRangeExplicitEndText",
      organizationObj: "selectedOrganization",
    }),
    parts() {
      return this.definition.parts;
    },
    dataUrl() {
      return this.$router.resolve({
        path: `/api/reporting/reports/${this.definition.name}/`,
        query: {
          start_date: this.dateRangeStart + "-01",
          end_date: this.dateRangeEnd + "-01",
          organization: this.organizationObj ? this.organizationObj.pk : null,
        },
      }).href;
    },
    sourceReportsObj() {
      let result = {};
      this.definition.dataSources.forEach((source) => {
        result[source.id ?? source.name ?? source.reportType] = source;
      });
      return result;
    },
  },

  methods: {
    async loadResults() {
      this.loading = true;
      let result = await this.http({
        url: this.dataUrl,
        method: "GET",
      });
      if (!result.error) {
        this.resultData = result.response.data;
        this.usedStartDate = this.dateRangeStart;
        this.usedEndDate = this.dateRangeEnd;
        this.usedOrganization = this.organizationObj;
      }
      this.loading = false;
    },
    runReport() {
      this.resultData = [];
      this.loadResults();
    },
  },

  watch: {
    definition() {
      this.resultData = [];
      this.usedOrganization = null;
      this.usedStartDate = null;
      this.usedEndDate = null;
    },
  },
};
</script>

<style lang="scss"></style>
