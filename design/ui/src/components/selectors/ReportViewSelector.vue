<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml">
en:
  standard_views: Standard views
  customizable_views: Customizable views

cs:
  standard_views: Standardní pohledy
  customizable_views: Nastavitelné pohledy
</i18n>
<template>
  <v-select
    :items="reportViewsForSelect"
    item-text="name"
    v-model="selectedReportView"
    :label="$t('available_report_types')"
    :return-object="true"
    outlined
    dense
    :loading="loading"
  >
    <template v-slot:item="{ item }">
      <v-list-item-content>
        <v-list-item-title v-html="item.name"></v-list-item-title>
        <v-list-item-subtitle
          v-if="item.desc"
          v-html="item.desc"
        ></v-list-item-subtitle>
      </v-list-item-content>
    </template>
  </v-select>
</template>
<script>
import axios from "axios";
import { isEqual } from "lodash";

export default {
  name: "ReportViewSelector",

  props: {
    value: { required: false, type: Object },
    reportViewsUrl: { required: true, type: String },
    viewFilter: { required: false, type: Function },
  },

  data() {
    return {
      selectedReportView: null,
      reportViews: [],
      loading: false,
    };
  },

  computed: {
    reportViewsForSelect() {
      let out = [];
      let allViews = this.reportViews;
      if (this.viewFilter) {
        allViews = allViews.filter(this.viewFilter);
      }
      let standard = allViews.filter((item) => item.is_standard_view);
      let other = allViews.filter((item) => !item.is_standard_view);
      if (standard.length) {
        out.push({
          header: this.$t("standard_views"),
          backgroundColor: "blue",
        });
        out = out.concat(standard);
      }
      if (other.length) {
        if (out.length) {
          out.push({ divider: true }); // add divider between standard and custom
        }
        out.push({ header: this.$t("customizable_views") });
        out = out.concat(other);
      }
      return out;
    },
  },

  methods: {
    async loadReportViews() {
      this.reportViews = [];
      let url = this.reportViewsUrl;
      if (url) {
        this.loading = true;
        try {
          const response = await axios.get(url);
          this.reportViews = response.data;
          if (this.reportViewsForSelect.length > 1) {
            let toSelect = null;
            if (this.preferFullReport) {
              // we need strict comparison to false because `is_standard_view` may be missing
              toSelect = this.reportViewsForSelect.find(
                (item) => item.is_standard_view === false
              );
            }
            // if there is something, [0] is header, [1] is actual reportView
            this.selectedReportView = toSelect
              ? toSelect
              : this.reportViewsForSelect[1];
          } else {
            this.selectedReportView = null;
          }
        } catch (error) {
          if (error.response?.status === 404) {
            // this is ok, it just means no views are available because the
            // platform is not connected to the organization
            this.reportViews = [];
            this.selectedReportView = null;
          } else {
            console.log("ERROR: ", error);
            this.showSnackbar({ content: "Error loading title: " + error });
          }
        } finally {
          this.loading = false;
        }
      }
    },
  },

  mounted() {
    this.loadReportViews();
  },

  watch: {
    value(val) {
      if (!isEqual(val, this.selectedReportView)) {
        this.selectedReportView = val;
      }
    },
    selectedReportView(val) {
      this.$emit("input", val);
    },
    reportViewsUrl() {
      this.loadReportViews();
    },
  },
};
</script>
