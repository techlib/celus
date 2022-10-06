<i18n lang="yaml" src="@/locales/common.yaml" />
<i18n lang="yaml" src="@/locales/errors.yaml" />
<i18n lang="yaml">
en:
  detail: Detail
  error: Error
  error_code: Error code
  error_intro: The following error was reported during the preparation of the report.
  available_parts: Select part - {count} available | Select part - {count} available | Select part - {count} available
  loading_parts: Loading list of parts

cs:
  detail: Detail
  error: Chyba
  error_code: Kód chyby
  error_intro: Následující chyba byla nahlášena při přípravě požadovaného reportu.
  available_parts: Vyberte část - {count} možnost | Vyberte část - {count} možnosti | Vyberte část - {count} možností
  loading_parts: Nahrávám seznam částí
</i18n>

<template>
  <div>
    <div v-if="loadingParts">
      <v-progress-linear indeterminate :height="24" class="mb-4">
        <span class="text-caption" v-text="$t('loading_parts')"></span>
      </v-progress-linear>
    </div>
    <v-data-table
      v-else-if="
        cleanData.length ||
        (loading && !errorCode) ||
        (report && report.splitBy && splitParts.length && currentPart)
      "
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

      <template #top v-if="report.splitBy && splitParts.length">
        <v-slide-group
          v-if="splitParts.length < 16"
          v-model="currentPart"
          class="py-4"
        >
          <v-slide-item
            v-for="item in splitParts"
            :key="item.id"
            v-slot="{ active, toggle }"
            :value="item.id"
          >
            <v-btn @click="toggle" :input-value="active" text outlined tile>{{
              item.text
            }}</v-btn>
          </v-slide-item>
        </v-slide-group>
        <!-- if there are too many parts, use a select -->
        <v-autocomplete
          v-else
          :items="splitParts"
          v-model="currentPart"
          :label="$tc('available_parts', splitParts.length)"
          item-value="id"
          class="py-4 ps-4"
          outlined
          dense
        />
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
import { toBase64JSON } from "@/libs/serialization";
import cancellation from "@/mixins/cancellation";

export default {
  name: "FlexiTableOutput",

  mixins: [translators, cancellation],

  props: {
    readonly: { default: false, type: Boolean },
    showZeroRows: { default: false, type: Boolean },
  },

  data() {
    return {
      report: null,
      part: null,
      data: [],
      cleanData: [],
      totalRowCount: null,
      loadingData: false,
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
      cancelTokenSource: null,
      splitParts: [],
      currentPart: null,
      loadingParts: false,
    };
  },

  computed: {
    loading() {
      return this.loadingData || this.dataComputing || this.translatorsUpdating;
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
          value: "target__" + key,
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

      // if we are in the split mode, we need to check the possible splits first
      this.splitParts = [];
      if (this.report.splitBy) {
        await this.getSplitParts();
      } else {
        this.currentPart = null;
      }

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
      this.errorCode = null;
      this.errorDetails = null;
      if (clean) {
        this.data = [];
        this.cleanData = [];
        this.setOrdering(report);
        this.options.page = 1;
      }
      await this.fetchData();
    },
    async getSplitParts() {
      this.loadingParts = true;
      let resp = await this.http({
        url: "/api/flexible-slicer/parts/",
        params: this.report.urlParams(),
      });
      if (resp.response) {
        let splitParts = resp.response.data.values.map(
          (item) => item[this.report.splitBy.ref]
        );
        // explicit dimensions do not have a translator defined by default,
        // so we need to define it if we are splitting by explicit mapped dimension
        if (this.report.splitBy.isExplicit && this.report.splitBy.isMapped) {
          this.translators[this.report.splitBy.ref] =
            this.translators.explicitDimension;
        }
        let translator = this.translators[this.report.splitBy.ref];
        if (translator) {
          await translator.prepareTranslation(splitParts);
          this.splitParts = splitParts
            .map((item) => {
              return {
                id: item,
                text: translator.translateKeyToString(item, this.$i18n.locale),
              };
            })
            .sort((a, b) => a.text.localeCompare(b.text));
        } else {
          this.splitParts = splitParts.map((item) => {
            return { id: item, text: item.toString() };
          });
        }
        this.splitParts.sort((a, b) => a.text.localeCompare(b.text));
        if (
          this.splitParts &&
          (!this.currentPart ||
            !this.splitParts.find((item) => item.id === this.currentPart))
        )
          this.currentPart = this.splitParts[0].id;
      }
      this.loadingParts = false;
    },
    cancelReport() {
      this.cancelTokenSource.cancel("request canceled by user");
    },
    async fetchData() {
      this.loadingData = true;
      this.cancelTokenSource = axios.CancelToken.source();
      let params = {
        ...this.report.urlParams(),
        page_size: this.options.itemsPerPage,
        page: this.options.page,
        ...this.orderByParam,
      };
      if (this.report.splitBy && this.currentPart) {
        params["part"] = toBase64JSON([this.currentPart]);
      }
      try {
        let resp = await axios({
          method: "GET",
          url: this.dataUrl,
          params: params,
          cancelToken: this.cancelTokenSource.token,
        });
        this.data = resp.data.results;
        this.totalRowCount = resp.data.count;
      } catch (error) {
        if (axios.isCancel(error)) {
          console.debug("Request cancelled by customer");
        } else if (
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
        this.loadingData = false;
        this.cancelTokenSource = null;
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
            let obj = this.translators[this.row].translateKey(newItem.pk);
            if (obj) {
              Object.keys(this.titleColumns).forEach((key) => {
                newItem["target__" + key] = obj[key];
              });
            }
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
    currentPart() {
      this.fetchData();
    },
  },
};
</script>
