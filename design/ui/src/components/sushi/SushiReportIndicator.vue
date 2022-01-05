<i18n lang="yaml" src="@/locales/sushi.yaml"></i18n>

<template>
  <v-tooltip bottom max-width="400">
    <template v-slot:activator="{ on }">
      <span v-on="on">
        <span>{{ report.code }}</span>
        <span v-if="showName && report.name" class="font-weight-light me-2"
          >: {{ report.name }}</span
        >
        <v-icon v-if="isBroken" x-small color="error" class="pl-1"
          >fa-exclamation</v-icon
        >
        <v-icon v-else-if="inKnowledgebase" x-small color="success" class="pl-1"
          >fa-user-check</v-icon
        >
        <v-icon v-if="inRegistry" small color="counterRegistry" class="pl-1"
          >fa-registered</v-icon
        >
      </span>
    </template>
    <span>
      <strong v-if="report.name">{{ report.name }}</strong>
      <strong v-else>{{ report.code }}</strong>
      <div v-if="inKnowledgebase">
        <v-icon small color="success">fa-user-check</v-icon>
        {{ $t("sushi.knowledgebase_report_type_desc") }}
      </div>
      <div v-if="isBroken">
        <v-icon small color="error">fa-exclamation-triangle</v-icon>
        {{ $t("sushi.broken_report_type_desc") }}
      </div>
      <div v-if="inRegistry">
        <v-icon small v-if="inRegistry" color="counterRegistry"
          >fa-registered</v-icon
        >
        {{ $t("sushi.registry_report_type_desc") }}
      </div>
    </span>
  </v-tooltip>
</template>

<script>
export default {
  name: "SushiReportIndicator",

  props: {
    report: {
      required: true,
      type: Object,
    },
    brokenFn: {
      // function to call with report instance to get its broken status
      required: false,
      default: null,
    },
    knowledgebaseFn: {
      // function to call with report instance to find out whether
      // the report type is in the knowledgebase
      required: false,
      default: null,
    },
    registryFn: {
      // function to call with report instance to find out whether
      // the report type is in the COUNTER registry
      required: false,
      default: null,
    },
    showName: {
      default: false,
      type: Boolean,
    },
  },

  computed: {
    isBroken() {
      if (this.brokenFn === false) {
        return false;
      } else if (this.brokenFn !== null) {
        return this.brokenFn(this.report);
      } else {
        return this.report.broken;
      }
    },
    inKnowledgebase() {
      if (this.knowledgebaseFn === false || this.knowledgebaseFn === null) {
        return false;
      } else {
        return this.knowledgebaseFn(this.report);
      }
    },
    inRegistry() {
      if (!this.registryFn) {
        return false;
      } else {
        return this.registryFn(this.report);
      }
    },
  },
};
</script>
