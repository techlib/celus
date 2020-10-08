<i18n lang="yaml" src="@/locales/sushi.yaml" />

<template>
  <LoaderWidget v-if="loading" icon-name="fa-cog" />
  <ve-pie
    v-else
    :data="chartData"
    :extend="chartExtend"
    :settings="chartSettings"
    :height="height"
  />
</template>

<script>
import VePie from "v-charts/lib/pie";
import axios from "axios";
import {
  attemptState,
  ATTEMPT_QUEUED,
  ATTEMPT_SUCCESS,
  ATTEMPT_ERROR,
  ATTEMPT_NOT_MADE,
  ATTEMPT_EMPTY_DATA,
  ATTEMPT_UNKNOWN,
} from "@/libs/attempt-state";
import LoaderWidget from "@/components/util/LoaderWidget";
import { mapActions } from "vuex";

export default {
  name: "SushiStatusChart",

  components: {
    VePie,
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
    let data = {
      showInactive: false,
      rawData: null,
      statusCounter: new Map(),
      loading: false,
      sushiCredentialsList: [],
      height: "370px",
      states: [
        ATTEMPT_NOT_MADE,
        ATTEMPT_QUEUED,
        ATTEMPT_SUCCESS,
        ATTEMPT_EMPTY_DATA,
        ATTEMPT_UNKNOWN,
        ATTEMPT_ERROR,
      ],
      statusToColor: {},
    };
    data.statusToColor[this.$t(`sushi.state.${ATTEMPT_QUEUED}`)] = "#9e9e9e";
    data.statusToColor[this.$t(`sushi.state.${ATTEMPT_SUCCESS}`)] = "#7dc17f";
    data.statusToColor[this.$t(`sushi.state.${ATTEMPT_ERROR}`)] = "#e58383";
    data.statusToColor[this.$t(`sushi.state.${ATTEMPT_NOT_MADE}`)] = "#e8e8e8";
    data.statusToColor[this.$t(`sushi.state.${ATTEMPT_EMPTY_DATA}`)] =
      "#a6cea7";
    data.statusToColor[this.$t(`sushi.state.${ATTEMPT_UNKNOWN}`)] = "#f8b765";
    return data;
  },

  computed: {
    credentialsUrl() {
      return `/api/sushi-credentials/?organization=${this.organizationId}`;
    },
    statsUrl() {
      let url = `/api/sushi-credentials/month-overview/?organization=${this.organizationId}&month=${this.month}`;
      if (this.showInactive) {
        url += "&disabled=true";
      }
      return url;
    },
    rows() {
      return this.states.map((state) => {
        return {
          status: this.$t(`sushi.state.${state}`),
          count: this.statusCounter.get(state),
        };
      });
    },
    chartData() {
      return {
        columns: ["status", "count"],
        rows: this.rows,
      };
    },
    chartSettings() {
      const legendName = {};
      for (let state of this.states) {
        legendName[state] = this.$t(`sushi.state.${state}`);
      }
      return {
        legendName: legendName,
      };
    },
    chartExtend() {
      const that = this;
      return {
        series(item) {
          for (let ser of item) {
            ser.data = ser.data.map((v) => ({
              ...v,
              // name: that.$t(`sushi.state.${v.name}`),
              // value: v.value,
              itemStyle: {
                color: that.statusToColor[v.name],
              },
            }));
          }
          return item;
        },
      };
    },
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    async loadSushiCredentialsList() {
      this.loading = true;
      try {
        let response = await axios.get(this.credentialsUrl);
        this.sushiCredentialsList = response.data;
        if (this.rawData) {
          this.prepareData();
        }
      } catch (error) {
        this.showSnackbar({
          content: "Error loading credentials list: " + error,
          color: "error",
        });
      } finally {
        this.loading = false;
      }
    },
    async fetchData() {
      if (!this.statsUrl) {
        return;
      }
      this.loading = true;
      try {
        let response = await axios.get(this.statsUrl);
        this.rawData = response.data;
        this.rawData.forEach((item) => (item.state = attemptState(item)));
        if (this.sushiCredentialsList) {
          this.prepareData();
        }
      } catch (error) {
        this.showSnackbar({
          content: "Error loading stats: " + error,
          color: "error",
        });
      } finally {
        this.loading = false;
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
            if (attemptMap.has(key)) {
              state = attemptMap.get(key).state;
            }
            statusCounter.set(state, (statusCounter.get(state) | 0) + 1);
          }
        });
      this.statusCounter = statusCounter;
    },
  },

  watch: {
    statsUrl() {
      this.loadSushiCredentialsList();
      this.fetchData();
    },
  },

  mounted() {
    this.loadSushiCredentialsList();
    this.fetchData();
  },
};
</script>

<style scoped></style>