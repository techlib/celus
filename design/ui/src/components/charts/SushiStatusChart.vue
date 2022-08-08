<i18n lang="yaml" src="@/locales/sushi.yaml"></i18n>

<template>
  <LoaderWidget v-if="loading" icon-name="fa-cog" height="370px" />
  <div v-else :style="{ height: height }">
    <v-chart :option="option" />
  </div>
</template>

<script>
import {
  ATTEMPT_SUCCESS,
  ATTEMPT_ERROR,
  ATTEMPT_IMPORT_FAILED,
  ATTEMPT_NOT_MADE,
  ATTEMPT_EMPTY_DATA,
  ATTEMPT_UNKNOWN,
  BROKEN_REPORT,
  BROKEN_CREDENTIALS,
} from "@/libs/attempt-state";

import {
  intentionState,
  INTENTION_QUEUED,
  INTENTION_WAITING,
} from "@/libs/intention-state";
import cancellation from "@/mixins/cancellation";

import LoaderWidget from "@/components/util/LoaderWidget";

/* vue-echarts */
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { PieChart } from "echarts/charts";
import { TooltipComponent, LegendComponent } from "echarts/components";
import VChart from "vue-echarts";
use([CanvasRenderer, TooltipComponent, LegendComponent, PieChart]);
/* ~vue-echarts */

export default {
  name: "SushiStatusChart",

  mixins: [cancellation],
  components: {
    VChart,
    LoaderWidget,
  },

  props: {
    month: {
      required: true,
      type: String,
    },
    organizationId: {
      default: -1,
      type: Number,
      required: false,
    },
  },

  data() {
    return {
      showInactive: false,
      rawData: null,
      statusCounter: new Map(),
      loadingCredentials: false,
      loadingStats: false,
      sushiCredentialsList: [],
      height: "370px",
      states: [
        ATTEMPT_NOT_MADE,
        INTENTION_QUEUED,
        INTENTION_WAITING,
        ATTEMPT_SUCCESS,
        ATTEMPT_EMPTY_DATA,
        ATTEMPT_UNKNOWN,
        ATTEMPT_ERROR,
        ATTEMPT_IMPORT_FAILED,
        BROKEN_REPORT,
        BROKEN_CREDENTIALS,
      ],
      statusToColor: {
        [INTENTION_QUEUED]: "#9e9e9e",
        [INTENTION_WAITING]: "#cacaca",
        [ATTEMPT_SUCCESS]: "#7dc17f",
        [ATTEMPT_ERROR]: "#e58383",
        [ATTEMPT_IMPORT_FAILED]: "#e58383",
        [ATTEMPT_NOT_MADE]: "#e8e8e8",
        [ATTEMPT_EMPTY_DATA]: "#a6cea7",
        [ATTEMPT_UNKNOWN]: "#f8b765",
        [BROKEN_CREDENTIALS]: "#bb4652",
        [BROKEN_REPORT]: "#c2545f",
      },
    };
  },

  computed: {
    loading() {
      return this.loadingCredentials || this.loadingStats;
    },
    statsParams() {
      if (!this.organizationId || !this.month) return null;

      return {
        organization: this.organizationId,
        month: this.month,
        ...(this.showInactive && { disabled: true }),
      };
    },
    option() {
      return {
        series: [
          {
            type: "pie",
            radius: "55%",
            center: ["50%", "60%"],
            data: this.states.map((state) => {
              return {
                name: this.$t(`sushi.state.${state}`),
                value: this.statusCounter.get(state),
                itemStyle: { color: this.statusToColor[state] },
                id: state,
              };
            }),
            emphasis: {
              scaleSize: 10,
            },
          },
        ],
        legend: {},
        tooltip: {},
      };
    },
  },

  methods: {
    async loadSushiCredentialsList() {
      this.loadingCredentials = true;
      try {
        const { response } = await this.http({
          url: "/api/sushi-credentials/",
          params: { organization: this.organizationId },
          label: "credentials list",
        });
        this.sushiCredentialsList = response ? response.data : [];
        if (this.rawData) {
          this.prepareData();
        }
      } finally {
        this.loadingCredentials = false;
      }
    },
    async fetchData() {
      if (!this.statsParams) return;

      this.loadingStats = true;
      try {
        const { response } = await this.http({
          url: "/api/sushi-credentials/month-overview/",
          params: this.statsParams,
          label: "stats",
        });
        this.rawData = response ? response.data : [];
        this.rawData.forEach((item) => (item.state = intentionState(item)));
        if (this.sushiCredentialsList) {
          this.prepareData();
        }
      } finally {
        this.loadingStats = false;
      }
    },
    prepareData() {
      // create a map to easily find the attempt data
      let attemptMap = new Map();
      this.rawData.forEach((item) =>
        attemptMap.set(`${item.credentials_id}-${item.counter_report_id}`, item)
      );

      let statusCounter = new Map();
      this.sushiCredentialsList
        .filter((item) => item.enabled)
        .forEach((item) => {
          for (let reportType of item.counter_reports_long) {
            let key = `${item.pk}-${reportType.id}`;
            let state = ATTEMPT_NOT_MADE;
            if (item.broken !== null) {
              state = BROKEN_CREDENTIALS;
            } else if (reportType.broken !== null) {
              state = BROKEN_REPORT;
            } else if (attemptMap.has(key)) {
              state = attemptMap.get(key).state;
            }
            statusCounter.set(state, (statusCounter.get(state) ?? 0) + 1);
          }
        });
      this.statusCounter = statusCounter;
    },
  },

  watch: {
    statsParams() {
      this.fetchData();
    },
    organizationId() {
      this.loadSushiCredentialsList();
    },
  },

  mounted() {
    this.loadSushiCredentialsList();
    this.fetchData();
  },
};
</script>

<style scoped></style>
