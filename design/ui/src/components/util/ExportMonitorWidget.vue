<i18n lang="yaml" src="@/locales/reporting.yaml" />
<i18n lang="yaml">
en:
  progress_tt: "|{current} out of {total} row exported so far|{current} out of {total} rows exported so far"
  waiting_for_start: Waiting for export to start
  exporting: Exporting
  download: Download

cs:
  progress_tt: "Zatím bylo vyexportováno {current} z {total} sloupce|Zatím bylo vyexportováno {current} ze {total} sloupců|Zatím bylo vyexportováno {current} z {total} sloupců"
  waiting_for_start: Čekám na spuštění exportu
  exporting: Exportuji
  download: Stáhnout
</i18n>

<template>
  <v-btn
    :href="outputFile"
    :color="color"
    :disabled="disabled"
    text
    v-if="status !== EXPORT_ERROR"
  >
    <v-tooltip bottom v-if="inProgress">
      <template #activator="{ on }">
        <span v-on="on">
          <v-progress-circular
            :value="progress"
            :indeterminate="progress === 0"
            height="24"
            dark
          >
            <span class="small-text">{{ progressText }}</span>
          </v-progress-circular>
          <span class="ml-2"
            >{{ $t("exporting")
            }}<span class="loading"
              ><span class="three-dots">&#x2026;</span></span
            ></span
          >
        </span>
      </template>
      {{ progressTooltip }}
    </v-tooltip>

    <span v-else>
      <v-icon small>fa fa-download</v-icon>
      <span class="ml-2">{{ $t("download") }}</span>
    </span>
  </v-btn>
  <span v-else>
    <v-tooltip bottom>
      <template #activator="{ on }">
        <span v-on="on" class="ml-4 text-button">
          <v-icon small color="warning">fa fa-exclamation-triangle</v-icon>
          <span class="ml-2 text-warning">{{ $t("export_status.error") }}</span>
        </span>
      </template>
      {{ errorText }}
    </v-tooltip>
  </span>
</template>

<script>
import axios from "axios";
import { mapActions } from "vuex";
import {
  EXPORT_ERROR,
  EXPORT_FINISHED,
  EXPORT_NOT_STARTED,
  EXPORT_IN_PROGRESS,
} from "@/libs/flexi-reports";

export default {
  name: "ExportMonitorWidget",

  props: {
    exportId: { required: true, type: Number },
    color: { default: "primary", type: String },
  },

  data() {
    return {
      exportDetails: null,
      forceProgress: false,
      doPoll: true,
      reloaded: false, // true if at least one reload of data was made
      EXPORT_ERROR,
      EXPORT_FINISHED,
    };
  },

  computed: {
    dataUrl() {
      return `/api/export/flexible-export/${this.exportId}/`;
    },
    status() {
      if (this.exportDetails) {
        return this.exportDetails.status;
      }
      return 0;
    },
    inProgress() {
      return (
        this.status === EXPORT_NOT_STARTED ||
        this.status === EXPORT_IN_PROGRESS ||
        this.forceProgress
      );
    },
    progress() {
      if (this.exportDetails && this.exportDetails.progress[1] > 0) {
        return (
          (100 * this.exportDetails.progress[0]) /
          this.exportDetails.progress[1]
        );
      }
      return 0;
    },
    progressText() {
      return `${Math.round(this.progress)}%`;
    },
    progressTooltip() {
      if (this.exportDetails && this.exportDetails.progress[1] > 0) {
        return this.$tc("progress_tt", this.exportDetails.progress[1], {
          current: this.exportDetails.progress[0],
          total: this.exportDetails.progress[1],
        });
      }
      return this.$t("waiting_for_start");
    },
    outputFile() {
      if (this.exportDetails && this.exportDetails.output_file) {
        return this.exportDetails.output_file;
      }
      return null;
    },
    disabled() {
      return !this.outputFile || this.status === EXPORT_ERROR;
    },
    errorText() {
      return this.exportDetails?.error_info?.detail ?? this.$t("error");
    },
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    async fetchData() {
      try {
        let resp = await axios.get(this.dataUrl);
        this.exportDetails = resp.data;
        if (this.doPoll && this.exportDetails.status < EXPORT_FINISHED) {
          setTimeout(this.fetchData, 500);
          this.reloaded = true;
        } else if (
          this.reloaded &&
          this.exportDetails.status >= EXPORT_FINISHED
        ) {
          this.$emit("finished", true);
        }
      } catch (error) {
        this.showSnackbar({
          content: "Could not update export details",
          color: "error",
        });
      }
    },
  },

  watch: {
    exportId: {
      immediate: true,
      handler() {
        this.fetchData();
      },
    },
  },

  beforeDestroy() {
    console.log("destroying");
    this.doPoll = false;
  },
};
</script>

<style scoped lang="scss">
.small-text {
  font-size: 75%;
}

.loading {
  display: inline-block;
  width: 1.25em;
  text-align: left;
}

.three-dots {
  overflow: hidden;
  display: inline-block;
  vertical-align: text-bottom;
  -webkit-animation: ellipsis steps(4, end) 900ms infinite;
  animation: ellipsis steps(4, end) 900ms infinite;
  //content: "\2026";
  width: 0px;
}

@keyframes ellipsis {
  to {
    width: 1.2em;
  }
}

@-webkit-keyframes ellipsis {
  to {
    width: 1.2em;
  }
}
</style>
