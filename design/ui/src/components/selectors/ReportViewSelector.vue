<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<i18n lang="yaml">
en:
  full_reports: Full reports
  standard_views: Standard views
  non_counter: non-COUNTER
cs:
  full_reports: Plné reporty
  standard_views: Standardní pohledy
  non_counter: non-COUNTER
</i18n>

<template>
  <div class="d-flex flex-row ga-6">
    <v-select
      :items="typesOfReportForSelect"
      item-title="name"
      item-value="pk"
      v-model="selectedTypeOfReport"
      :label="$t('type_of_report')"
      variant="outlined"
      density="compact"
      :return-object="true"
      :loading="loading"
      style="flex-basis: 50%"
      hide-details
    >
    </v-select>
    <v-select
      :items="reportViewsForSelect"
      item-title="name"
      item-value="pk"
      v-model="selectedReportView"
      :label="$t('report')"
      :return-object="true"
      variant="outlined"
      density="compact"
      :loading="loading"
      style="flex-basis: 50%"
      hide-details
    >
      <template v-slot:item="{ item, props }">
        <v-list-item class="active_item" v-if="item.raw.name" v-bind="props">
          <div class="d-flex flex-column">
            <div
              class="v-list-item-subtitle"
              v-if="item.raw.desc"
              v-html="item.raw.desc"
            ></div>
          </div>
        </v-list-item>
        <v-list-item class="disabled_item" v-else>
          {{ item.raw.header }}
        </v-list-item>
      </template>
    </v-select>
  </div>
</template>

<script>
import axios from "axios";
import { isEqual } from "lodash";
import { mapActions } from "vuex";

export default {
  name: "ReportViewSelector",

  props: {
    modelValue: { required: false, type: Object },
    reportViewsUrl: { required: true, type: String },
    viewFilter: { required: false, type: Function },
    preferFullReport: { required: false, type: Boolean, default: false },
  },

  data() {
    return {
      selectedReportView: null,
      selectedTypeOfReport: null,
      reportViews: [],
      loading: false,
    };
  },

  computed: {
    typesOfReportForSelect() {
      let allViews = this.reportViews;
      if (this.viewFilter) {
        allViews = allViews.filter(this.viewFilter);
      }

      let out = [];
      if (allViews.some((e) => e.type == "interest")) {
        out.push({ name: this.$t("interest"), value: "interest" });
      }
      if (allViews.some((e) => e.type == "counter51")) {
        out.push({ name: "COUNTER 5.1", value: "counter51" });
      }
      if (allViews.some((e) => e.type == "counter5")) {
        out.push({ name: "COUNTER 5", value: "counter5" });
      }
      if (allViews.some((e) => e.type == "counter4")) {
        out.push({ name: "COUNTER 4", value: "counter4" });
      }
      if (allViews.some((e) => e.type == "non-counter")) {
        out.push({ name: this.$t("non_counter"), value: "non-counter" });
      }

      return out;
    },
    hasSubreports() {
      switch (this.selectedTypeOfReport?.value) {
        case "interest":
        case "counter4":
        case "non-counter":
          return false;
        default:
          return true;
      }
    },
    reportViewsForSelect() {
      let out = [];
      let allViews = this.reportViews;
      if (this.viewFilter) {
        allViews = allViews.filter(this.viewFilter);
      }
      allViews = allViews.filter(
        (e) => e.type == this.selectedTypeOfReport?.value,
      );
      let standard = allViews.filter((item) => item.is_standard_view);
      let other = allViews.filter((item) => !item.is_standard_view);
      if (other.length) {
        this.hasSubreports && out.push({ header: this.$t("full_reports") });
        out = out.concat(other);
      }
      if (standard.length) {
        this.hasSubreports && out.push({ header: this.$t("standard_views") });
        out = out.concat(standard);
      }
      return out;
    },
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    async loadReportViews() {
      this.reportViews = [];
      let url = this.reportViewsUrl;
      if (url) {
        this.loading = true;
        try {
          const response = await axios.get(url);
          this.reportViews = response.data;
          for (let report_view of this.reportViews) {
            if (report_view.is_interest) {
              report_view.type = "interest";
            } else if (report_view.counter_version) {
              report_view.type = `counter${report_view.counter_version}`;
            } else {
              report_view.type = "non-counter";
            }
          }
          this.selectTypeOfReportWhenEmpty();
        } catch (error) {
          if (error.response?.status === 404) {
            // this is ok, it just means no views are available because the
            // platform is not connected to the organization
            this.reportViews = [];
            this.selectedReportView = null;
          } else {
            this.showSnackbar({ content: "Error loading title: " + error });
          }
        } finally {
          this.loading = false;
        }
      }
    },
    selectTypeOfReportWhenEmpty() {
      if (
        this.typesOfReportForSelect &&
        this.typesOfReportForSelect.length > 0
      ) {
        const available = this.typesOfReportForSelect.map((e) => e.value);
        if (!available.includes(this.selectedTypeOfReport?.value)) {
          this.selectedTypeOfReport = this.typesOfReportForSelect[0];
          this.selectReportViewWhenEmpty();
        }
      }
    },
    selectReportViewWhenEmpty() {
      if (this.reportViewsForSelect && this.reportViewsForSelect.length > 0) {
        const available = this.typesOfReportForSelect
          .filter((e) => !!e.pk)
          .map((e) => e.pk);
        if (!available.includes(this.selectedReportView?.pk)) {
          let toSelect = null;
          if (this.preferFullReport) {
            // we need strict comparison to false because `is_standard_view` may be missing
            toSelect = this.reportViewsForSelect.find(
              (item) => item.is_standard_view === false,
            );
          }
          // if there is something, [0] is header, [1] is actual reportView
          this.selectedReportView = toSelect
            ? toSelect
            : this.reportViewsForSelect.filter((e) => !!e.pk)[0];
        }
      } else {
        this.selectedReportView = null;
      }
    },
  },

  mounted() {
    this.loadReportViews();
  },

  watch: {
    modelValue(val) {
      if (!isEqual(val, this.selectedReportView)) {
        this.selectedReportView = val;
      }
    },
    selectedReportView(val) {
      this.$emit("update:modelValue", val);
    },
    reportViewsUrl() {
      this.loadReportViews();
    },
    selectedTypeOfReport(val) {
      if (!val) {
        this.selectedReportView = null;
      } else {
        this.selectReportViewWhenEmpty();
      }
      if (!this.selectedTypeOfReport) {
        if (this.reportViewsForSelect.length > 1) {
          let toSelect = null;
          if (this.preferFullReport) {
            // we need strict comparison to false because `is_standard_view` may be missing
            toSelect = this.reportViewsForSelect.find(
              (item) => item.is_standard_view === false,
            );
          }
          // if there is something, [0] is header, [1] is actual reportView
          this.selectedReportView = toSelect
            ? toSelect
            : this.reportViewsForSelect[1];
        } else {
          this.selectedReportView = null;
        }
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.disabled_item {
  font-size: 80%;
  background-color: #ededed;
  min-height: 35px !important;
  color: rgba(0, 0, 0, 0.6);
}

.active_item {
  padding-left: 25px !important;
}
</style>
