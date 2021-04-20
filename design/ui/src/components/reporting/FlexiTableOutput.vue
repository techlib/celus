<i18n lang="yaml" src="@/locales/common.yaml" />
<i18n lang="yaml" src="@/locales/errors.yaml" />
<i18n lang="yaml">
en:
  detail: Detail
  error: Error
  error_code: Error code
  error_intro: The following error was reported during the preparation of the report.

cs:
  detail: Detail
  error: Chyba
  error_code: Kód chyby
  error_intro: Následující chyba byla nahlášena při přípravě požadovaného reportu.
</i18n>

<template>
  <v-data-table
    v-if="cleanData.length || (loading && !errorCode)"
    :items="cleanData"
    :headers="tableHeaders"
    item-key="pk"
    :loading="loading"
    dense
    :footer-props="{ itemsPerPageOptions: [20, 50, 100] }"
    :options.sync="options"
    :server-items-length="totalRowCount"
  >
    <template #loading>
      <v-skeleton-loader type="paragraph@10" loading class="py-10 px-5" />
    </template>
  </v-data-table>
  <div v-else-if="errorCode">
    <v-card>
      <v-card-title>
        <v-icon color="error" class="mr-2">fa fa-exclamation-triangle</v-icon>
        {{ $t("error") }}
      </v-card-title>
      <v-card-text>
        <p>{{ $t("error_intro") }}</p>
        <p>
          <strong>{{ $t("error_code") }}</strong
          >: {{ errorCode }}
        </p>
        <p>
          <strong>{{ $t("detail") }}</strong
          >: {{ errorText }}
        </p>
      </v-card-text>
    </v-card>
  </div>
</template>
<script>
import axios from "axios";
import { splitGroup } from "@/libs/group-ids";
import { formatInteger } from "@/libs/numbers";
import { mapActions } from "vuex";
import translators from "@/mixins/translators";
import { djangoToDataTableOrderBy } from "@/libs/sorting";
import { isEqual } from "lodash";

export default {
  name: "FlexiTableOutput",

  mixins: [translators],

  props: {
    readonly: { default: false, type: Boolean },
  },

  data() {
    return {
      report: null,
      data: [],
      cleanData: [],
      totalRowCount: null,
      dataLoading: false,
      dataComputing: false,
      translatorsUpdating: false,
      headersFromData: [],
      options: { itemsPerPage: 20, page: 1 },
      titleColumns: {
        issn: true,
        eissn: true,
        isbn: true,
        doi: false,
      },
      errorCode: null,
      errorDetails: null,
    };
  },

  computed: {
    loading() {
      return this.dataLoading || this.dataComputing || this.translatorsUpdating;
    },
    activeTitleColumns() {
      let titleHeaders = [];
      if (this.report.primaryDimension.ref === "target") {
        titleHeaders = Object.entries(this.titleColumns)
          .filter(([key, value]) => value)
          .map(([key, value]) => key);
      }
      return titleHeaders;
    },
    tableHeaders() {
      if (this.report) {
        let headers = [];
        this.headersFromData.forEach((item) =>
          headers.push({ ...item, sortable: !this.readonly })
        );
        let titleHeaders = this.activeTitleColumns.map((key) => ({
          text: this.$t("title_fields." + key),
          value: key,
        }));
        let ret = [
          {
            text: this.report.primaryDimension.getName(this.$i18n),
            value: this.report.primaryDimension.ref,
            sortable: !this.readonly,
          },
          ...titleHeaders,
          ...headers,
        ];
        return ret;
      }
      return [];
    },
    row() {
      return this.report.primaryDimension.ref;
    },
    dataUrl() {
      return "/api/flexible-slicer/";
    },
    orderByParam() {
      let prefix = this.options.sortDesc && this.options.sortDesc[0] ? "-" : "";
      if (this.options.sortBy && this.options.sortBy.length) {
        return { order_by: prefix + this.options.sortBy[0] };
      }
      return {};
    },
    errorText() {
      if (this.errorCode) {
        return this.$t(this.errorCode, this.errorDetails);
      }
      return "";
    },
  },

  methods: {
    ...mapActions(["showSnackbar"]),
    async updateOutput(report, clean = true) {
      this.report = report;
      // update translators
      this.report.groupBy
        .filter((item) => item.isExplicit)
        .forEach((item) => {
          if (item.isMapped) {
            this.translators[item.ref] = this.translators.explicitDimension;
          } else {
            this.translators[item.ref] = null;
          }
        });
      let primDim = this.report.primaryDimension;
      if (primDim.isExplicit && primDim.isMapped) {
        this.translators[primDim.ref] = this.translators.explicitDimension;
      }
      if (clean) {
        this.data = [];
        this.cleanData = [];
        this.setOrdering(report);
      }
      await this.fetchData();
    },
    async fetchData() {
      this.dataLoading = true;
      let params = {
        ...this.report.urlParams(),
        page_size: this.options.itemsPerPage,
        page: this.options.page,
        ...this.orderByParam,
      };
      try {
        let resp = await axios.get(this.dataUrl, {
          params: params,
        });
        this.data = resp.data.results;
        this.totalRowCount = resp.data.count;
      } catch (error) {
        if (
          error.response.data &&
          error.response.data.error &&
          error.response.data.error.code
        ) {
          let code = error.response.data.error.code;
          this.showError(code, error.response.data.error.details);
        } else {
          this.showSnackbar({
            content: "Could not load data: " + error,
            color: "error",
          });
        }
        return;
      } finally {
        this.dataLoading = false;
      }
      await this.updateTranslators();
      this.recomputeData();
    },
    async updateTranslators() {
      this.translatorsUpdating = true;
      let promises = [];
      if (this.row && this.translators[this.row]) {
        // for implicit dimensions the key is 'pk' for explicit it is the name of the dim (e.g. dim1)
        let pks = this.data.map((item) => item.pk ?? item[this.row]);
        promises.push(this.translators[this.row].prepareTranslation(pks));
      }
      if (this.data.length > 0) {
        let pks_lists = Object.keys(this.data[0])
          .filter((item) => item !== "pk" && item !== this.row)
          .filter((item) => item.substr(0, 4) === "grp-")
          .map((item) => splitGroup(item));
        let i = 0;
        for (let group of this.report.groupBy) {
          let pks = pks_lists.map((item) => item[i]);
          if (this.translators[group.ref]) {
            promises.push(this.translators[group.ref].prepareTranslation(pks));
          }
          i++;
        }
      }
      await Promise.all(promises);
      this.translatorsUpdating = false;
    },
    recomputeData() {
      this.dataComputing = true;
      // process the data to translate the primary dimension
      this.cleanData = this.data.map((item) => {
        let newItem = { ...item };
        if (this.translators[this.row]) {
          newItem[this.row] =
            this.translators[this.row].translateKeyToString(
              newItem.pk ?? newItem[this.row],
              this.$i18n.locale
            ) ?? this.$t("blank_value");
          if (this.row === "target") {
            // extra data for titles
            let obj = this.translators[this.row].translateKey(
              newItem.pk ?? newItem[this.row]
            );
            Object.keys(this.titleColumns).forEach((key) => {
              newItem[key] = obj[key];
            });
          }
        }
        for (let key of Object.keys(newItem)) {
          if (key.substr(0, 4) === "grp-") {
            newItem[key] = formatInteger(newItem[key]);
          }
        }
        return newItem;
      });
      // extract the header row data
      let headersFromData = [];
      if (this.data.length > 0) {
        for (let key of Object.keys(this.data[0]).filter(
          (item) => item.substr(0, 4) === "grp-"
        )) {
          let pks = splitGroup(key);
          let texts = [];
          let i = 0;
          for (let group of this.report.groupBy) {
            if (this.translators[group.ref]) {
              texts.push(
                this.translators[group.ref].translateKeyToString(
                  pks[i],
                  this.$i18n.locale
                ) ?? "-"
              );
            } else {
              texts.push(pks[i]);
            }
            i++;
          }
          let text = texts.join(" / ");
          headersFromData.push({ text: text, value: key, align: "right" });
        }
      }
      this.headersFromData = headersFromData.sort((a, b) =>
        a.text.localeCompare(b.text)
      );
      this.dataComputing = false;
    },
    showError(code, details) {
      this.errorCode = code;
      this.errorDetails = details;
    },
    setOrdering(report) {
      let ob = djangoToDataTableOrderBy(report.orderBy);
      this.options.sortBy = ob.sortBy;
      this.options.sortDesc = ob.sortDesc;
    },
  },

  watch: {
    options: {
      deep: true,
      handler(oldVal, newVal) {
        if (!this.loading && !isEqual(newVal, oldVal)) {
          this.fetchData();
        }
      },
    },
  },
};
</script>
