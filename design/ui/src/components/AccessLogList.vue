<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<template>
  <v-data-table
    :items="accessLogs"
    :headers="headers"
    :sort-by.sync="orderBy"
    :sort-desc.sync="orderDesc"
    :loading="loading"
    :server-items-length="total"
    :page.sync="page"
    :items-per-page.sync="ipp"
    :footer-props="{ itemsPerPageOptions: [10, 25, 50] }"
    dense
  >
  </v-data-table>
</template>

<script>
import { mapActions } from "vuex";
import cancellation from "@/mixins/cancellation";

export default {
  name: "AccessLogList",

  mixins: [cancellation],

  props: {
    // one of the following two has to be set
    importBatch: { required: false, type: Number },
    mduId: { required: false, type: Number },
    showOrganization: { required: false, type: Boolean, default: false },
  },

  data() {
    return {
      accessLogs: [],
      orderBy: "target",
      orderDesc: false,
      loading: false,
      ipp: 10,
      page: 1,
      total: 0,
    };
  },

  computed: {
    headers() {
      return [
        {
          text: this.$i18n.t("labels.date"),
          value: "date",
        },
        ...(this.showOrganization
          ? [
              {
                text: this.$i18n.t("labels.organization"),
                value: "organization",
              },
            ]
          : []),
        {
          text: this.$i18n.t("labels.title"),
          value: "target",
        },
        ...this.dynamicHeaders,
        {
          text: this.$i18n.t("labels.metric"),
          value: "metric",
        },
        {
          text: this.$i18n.t("labels.value"),
          value: "value",
        },
      ];
    },
    dynamicHeaders() {
      let headers = [];
      if (this.accessLogs.length > 0) {
        for (let key of Object.keys(this.accessLogs[0])) {
          if (
            key !== "date" &&
            key !== "metric" &&
            key !== "value" &&
            key !== "organization" &&
            key !== "platform" &&
            key !== "report_type" &&
            key !== "target" &&
            key !== "row"
          ) {
            headers.push({
              text: key.replace(/_/g, " "),
              value: key,
              sortable: false,
            });
          }
        }
      }
      return headers;
    },
    queryUrl() {
      let url = "";
      if (this.importBatch) {
        url = "/api/ib-access-logs/" + this.importBatch + "/";
      } else if (this.mduId) {
        url = "/api/mdu-access-logs/" + this.mduId + "/";
      } else {
        console.error('Either "importBatch" or "mduId" must be set');
        return;
      }
      return this.$router.resolve({
        path: url,
        query: {
          page: this.page,
          page_size: this.ipp,
          order_by: this.orderBy,
          desc: this.orderDesc,
        },
      }).href;
    },
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    async loadLogs() {
      if (!this.queryUrl) {
        return;
      }
      this.loading = true;
      let resp = await this.http({ url: this.queryUrl });
      if (!resp.error) {
        this.accessLogs = resp.response.data.results;
        this.total = resp.response.data.count;
      } else {
        this.accessLogs = [];
        this.total = 0;
      }
      this.loading = false;
    },
  },

  watch: {
    queryUrl() {
      this.loadLogs();
    },
  },

  mounted() {
    this.loadLogs();
  },
};
</script>

<style scoped></style>
