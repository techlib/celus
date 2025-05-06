<i18n lang="yaml" src="@/locales/sushi.yaml"></i18n>

<template>
  <v-tooltip location="bottom" max-width="400">
    <template v-slot:activator="{ props }">
      <span
        v-bind="props"
        :style="{ width: '100%', display: 'flex', 'align-items': 'center' }"
      >
        <span :class="anyIcon ? 'pr-1' : ''">{{ report.code }}</span>
        <span v-if="showVersion"
          >: {{ counterVersionToStr(report.counter_version) }}</span
        >
        <span v-if="showName && report.name" class="font-weight-light me-2"
          >: {{ report.name }}</span
        >
        <v-icon v-if="isBroken" size="x-small" color="error" class="pl-1"
          >fas fa-exclamation</v-icon
        >
        <v-icon
          v-else-if="inKnowledgebase"
          size="x-small"
          color="success"
          class="pl-1 w-auto"
          >fas fa-user-check</v-icon
        >
        <v-icon
          v-if="inRegistry"
          size="small"
          color="counterRegistry"
          class="pl-1 w-auto"
          >fa fa-registered</v-icon
        >
      </span>
    </template>
    <span>
      <strong v-if="report.name">{{ report.name }}</strong>
      <strong v-else>{{ report.code }}</strong>
      <div v-if="inKnowledgebase">
        <v-icon size="small" color="success">fas fa-user-check</v-icon>
        {{ $t("sushi.knowledgebase_report_type_desc") }}
      </div>
      <div v-if="isBroken">
        <v-icon size="small" color="error">fa fa-exclamation-triangle</v-icon>
        {{ $t("sushi.broken_report_type_desc") }}
      </div>
      <div v-if="inRegistry">
        <v-icon size="small" v-if="inRegistry" color="counterRegistry"
          >fa fa-registered</v-icon
        >
        {{ $t("sushi.registry_report_type_desc") }}
      </div>
    </span>
  </v-tooltip>
</template>

<script>
import { counterVersionToStr } from "@/libs/sushi";

export default {
  name: "SushiReportIndicator",

  props: {
    report: {
      required: true,
      type: Object,
    },
    credentials: {
      required: false,
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
    showVersion: {
      default: false,
      type: Boolean,
    },
    IsAutocomplete: {
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
    anyIcon() {
      return this.isBroken || this.inKnowledgebase || this.inRegistry;
    },
  },

  methods: {
    counterVersionToStr,
  },
};
</script>
