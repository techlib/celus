<i18n lang="yaml" src="@/locales/sushi.yaml"></i18n>

<template>
  <v-tooltip bottom max-width="400">
    <template v-slot:activator="{ on }">
      <span v-on="on">
        {{ report.code }}
        <v-icon v-if="isBroken" x-small color="error" class="pl-1"
          >fa-exclamation</v-icon
        >
      </span>
    </template>
    <span>
      <strong v-if="report.name">{{ report.name }}</strong>
      <strong v-else>{{ report.code }}</strong>
      <div v-if="isBroken">
        <v-icon small color="error">fa-exclamation-triangle</v-icon>
        {{ $t("sushi.broken_report_type_desc") }}
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
  },
};
</script>
