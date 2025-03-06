<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<template>
  <v-data-table-server
    :items="accessLogs"
    :headers="headers"
    v-model:sort-by="sortBy"
    :loading="loading"
    :items-length="total"
    v-model:page="page"
    v-model:items-per-page="ipp"
    :footer-props="{ itemsPerPageOptions: [10, 25, 50] }"
  >
  </v-data-table-server>
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
      sortBy: [{ key: "target", order: "asc" }],
      loading: false,
      ipp: 10,
      page: 1,
      total: 0,
    };
  },

  computed: {
    headers() {
      let out = [
        {
          title: this.$i18n.t("labels.date"),
          value: "date",
          key: "date",
        },
        ...(this.showOrganization
          ? [
              {
                title: this.$i18n.t("labels.organization"),
                value: "organization",
                key: "organization",
              },
            ]
          : []),
        {
          title: this.$i18n.t("labels.title"),
          value: "target",
          key: "target",
          sortable: true,
        },
        ...this.dynamicHeaders,
        {
          title: this.$i18n.t("labels.metric"),
          value: "metric",
          key: "metric",
        },
        {
          title: this.$i18n.t("labels.value"),
          value: "value",
          key: "value",
        },
      ];
      return out.filter(
        (header) =>
          this.nonEmptyAttrs.has(header.value) || header.value === "value",
      );
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
            key !== "item" &&
            key !== "row"
          ) {
            headers.push({
              title: key.replace(/_/g, " "),
              value: key,
              sortable: false,
            });
          }
        }
      }
      return headers;
    },
    nonEmptyAttrs() {
      return new Set(
        this.accessLogs
          .map((log) =>
            Object.entries(log)
              .filter((e) => !!e[1])
              .map((e) => e[0]),
          )
          .flat(),
      );
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

      const sortKey = this.sortBy?.[0]?.key || "target";
      const orderDesc = this.sortBy?.[0]?.order === "desc" ? true : false;
      return this.$router.resolve({
        path: url,
        query: {
          page: this.page,
          page_size: this.ipp,
          order_by: sortKey,
          desc: orderDesc,
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

<style scoped lang="scss">
:deep(.v-data-table__tr) {
  &:hover {
    background-color: #00000016;
  }
}
</style>
