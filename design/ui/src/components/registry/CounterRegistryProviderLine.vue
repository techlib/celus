<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml" src="@/locales/counter_registry.yaml"></i18n>

<template>
  <tr :class="inRegistry?.url != inCelus?.url ? 'bg-red-lighten-5' : ''">
    <th>C{{ counterVersion }} URL</th>
    <td
      v-if="!inRegistry?.url && !inCelus?.url"
      colspan="2"
      class="text-center"
    >
      <i
        ><strong>{{ $t("counter_registry.missing_url") }}</strong></i
      >
    </td>
    <td :class="registryUrlClass" v-else>
      {{ inRegistry?.url }}
    </td>
    <td :class="celusUrlClass">{{ inCelus?.url }}</td>
  </tr>
  <tr
    :class="
      !sameReports(inRegistry?.reports, inCelus?.reports)
        ? 'bg-red-lighten-5'
        : ''
    "
  >
    <th>C{{ counterVersion }} {{ $t("counter_registry.counter_reports") }}</th>
    <td>
      <v-chip
        class="mr-1"
        size="small"
        label
        variant="flat"
        :color="
          !sameReports(inRegistry?.reports, inCelus?.reports) && checked
            ? 'error'
            : 'primary'
        "
        :key="report_name"
        v-for="report_name in inRegistry?.reports || []"
        >{{ report_name }}</v-chip
      >
    </td>
    <td>
      <v-chip
        class="mr-1"
        size="small"
        label
        variant="flat"
        :color="
          sameReports(inRegistry?.reports, inCelus?.reports) && checked
            ? 'error'
            : 'primary'
        "
        :key="report_name"
        v-for="report_name in inCelus?.reports || []"
        >{{ report_name }}</v-chip
      >
    </td>
  </tr>
</template>

<script>
import SushiReportIndicator from "@/components/sushi/SushiReportIndicator";

export default {
  name: "CounterRegistryProviderLine",
  components: {
    SushiReportIndicator,
  },
  props: {
    counterVersion: {
      required: true,
      type: String,
    },
    inRegistry: {
      required: true,
      type: Object,
    },
    inCelus: {
      required: true,
      type: Object,
    },
    checked: {
      required: true,
      type: Boolean,
    },
  },

  data() {
    return {};
  },

  computed: {
    registryUrlClass() {
      if (this.checked) {
        if (!this.inCelus || this.inCelus?.url != this.inRegistry?.url) {
          return "font-weight-bold";
        }
      }
      return "";
    },
    celusUrlClass() {
      if (this.checked) {
        if (!this.inRegistry || this.inCelus?.url == this.inRegistry?.url) {
          return "font-weight-bold";
        }
      }
      return "";
    },
  },

  methods: {
    sameReports(reports1, reports2) {
      if (!reports1 || !reports2) {
        return false;
      }
      reports1.sort();
      reports2.sort();
      return JSON.stringify(reports1) == JSON.stringify(reports2);
    },
  },

  watch: {},

  mounted() {},
};
</script>
