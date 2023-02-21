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
      <SpecializedReportLine
        v-for="(definition, index) in reportDefinitions"
        :name="definition.name"
        :description="definition.description"
        :mainReportDefinition="definition.mainReportDefinition"
        :fallbackReportDefinition="definition.fallbackReportDefinition"
        :subtractedFallbackReportDefinition="
          definition.subtractedFallbackReportDefinition
        "
        :implementationNote="definition.implementationNote"
        :key="definition.name"
        :data="resultData[index] ? resultData[index].data : []"
        :loading="loading"
      />
    </v-expansion-panels>
  </div>
</template>

<script>
import cancellation from "@/mixins/cancellation";
import SpecializedReportLine from "@/components/special/SpecializedReportLine";
import { mapGetters } from "vuex";

export default {
  name: "SpecializedReport",

  mixins: [cancellation],

  components: { SpecializedReportLine },

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
    reportDefinitions() {
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
