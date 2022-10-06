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
  no_data: No data matching the current setup was found.

cs:
  detail: Detail
  error: Chyba
  error_code: Kód chyby
  error_intro: Následující chyba byla nahlášena při přípravě požadovaného reportu.
  available_parts: Vyberte část - {count} možnost | Vyberte část - {count} možnosti | Vyberte část - {count} možností
  loading_parts: Nahrávám seznam částí
  no_data: Nebyla nalezena žádná data odpovídající aktuálnímu nastavení.
</i18n>

<template>
  <div ref="base" v-resize="updateSize">
    <div v-if="loadingParts">
      <v-progress-linear indeterminate :height="24" class="mb-4">
        <span class="text-caption" v-text="$t('loading_parts')"></span>
      </v-progress-linear>
    </div>

    <div
      v-else-if="
        cleanData.length ||
        (loading && !errorCode) ||
        (report && report.splitBy && splitParts.length && currentPart)
      "
    >
      <!-- part selector -->
      <div class="d-flex py-4 justify-space-between">
        <div v-if="report.splitBy && splitParts.length">
          <v-slide-group v-if="partsSideBySide" v-model="currentPart">
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
            outlined
            dense
          />
        </div>
        <div v-else></div>

        <div class="ps-4">
          <v-btn-toggle v-model="view" dense>
            <v-btn value="table"><v-icon small>fa-table</v-icon></v-btn>
            <v-btn value="chart"><v-icon small>fa-chart-bar</v-icon></v-btn>
          </v-btn-toggle>
        </div>
      </div>

      <v-data-table
        v-if="view === 'table'"
        :items="formattedData"
        :headers="tableHeaders"
        item-key="pk"
        :loading="loading"
        dense
        :footer-props="{ itemsPerPageOptions: itemsPerPageOptions }"
        :options.sync="options"
        :server-items-length="totalRowCount"
      >
        <template #loading>
          <v-skeleton-loader type="paragraph@10" loading class="py-10 px-5" />
        </template>

        <template #item.tag="{ item }">
          <TagChip :tag="item.tag" show-class small />
        </template>

        <template #item.assignedTags="{ item }">
          <TagChip
            v-for="tag in objIdToTags.get(item.pk)"
            :key="tag.pk"
            :tag="tag"
            small
            show-class
          />
        </template>
      </v-data-table>

      <ReportingChart
        v-else
        :data="cleanData"
        :primary-dimension="row"
        :secondary-dimension="report.groupBy[0].ref"
        :series="chartSeries"
        :type="row.startsWith('date') ? 'histogram' : 'bar'"
        :height="
          (row.startsWith('date') ? 480 : 260 + cleanData.length * 20) + 'px'
        "
      />
    </div>

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

    <div v-else-if="report">
      <v-alert type="info" outlined>{{ $t("no_data") }}</v-alert>
    </div>
  </div>
</template>
<script>
import axios from "axios";
import { splitGroup } from "@/libs/group-ids";
import { formatInteger } from "@/libs/numbers";
import { mapActions, mapGetters, mapState } from "vuex";
import translators from "@/mixins/translators";
import { djangoToDataTableOrderBy } from "@/libs/sorting";
import { isEqual } from "lodash";
import { toBase64JSON } from "@/libs/serialization";
import cancellation from "@/mixins/cancellation";
import TagChip from "@/components/tags/TagChip";
import ReportingChart from "@/components/reporting/ReportingChart";
import tags from "@/mixins/tags";

export default {
  name: "FlexiTableOutput",
  components: { TagChip, ReportingChart },
  mixins: [translators, cancellation, tags],

  props: {
    readonly: { default: false, type: Boolean },
    showZeroRows: { default: false, type: Boolean },
    // if the organization and selected dates should be used from the UI,
    // and not from the report, set this to true
    contextOverride: { default: false, type: Boolean },
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
      options: { itemsPerPage: this.contextOverride ? -1 : 20, page: 1 },
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
      view: "table",
      baseWidth: 0,
      rowToTagScope: {
        target: "title",
        platform: "platform",
        organization: "organization",
      },
    };
  },

  computed: {
    ...mapGetters({
      enableTags: "enableTags",
      dateRangeStart: "dateRangeStartText",
      dateRangeEnd: "dateRangeEndText",
    }),
    ...mapState({
      selectedOrganizationId: "selectedOrganizationId",
    }),
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
        let tagHeaders =
          this.taggableRow && this.enableTags
            ? [
                {
                  text: this.$t("labels.tags"),
                  value: "assignedTags",
                  sortable: false,
                },
              ]
            : [];
        let ret = [
          {
            text: this.report.effectivePrimaryDimension.getName(this.$i18n),
            value: this.report.effectivePrimaryDimension.ref,
            sortable: !this.readonly,
          },
          ...tagHeaders,
          ...titleHeaders,
          ...headers,
        ];
        return ret;
      }
      return [];
    },
    row() {
      return this.report.effectivePrimaryDimension.ref;
    },
    taggableRow() {
      return this.row in this.rowToTagScope;
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
    chartSeries() {
      return Object.fromEntries(
        this.headersFromData.map((item) => [item.value, item.text])
      );
    },
    formattedData() {
      return this.cleanData.map((item) => {
        let newItem = { ...item };
        for (let key of Object.keys(newItem)) {
          if (key.substr(0, 4) === "grp-") {
            newItem[key] = formatInteger(newItem[key]);
          }
        }
        return newItem;
      });
    },
    partsSideBySide() {
      if (this.baseWidth && this.splitParts.length) {
        const textWidth = this.splitParts.reduce(
          (acc, item) => acc + item.text.length,
          0
        );
        return this.baseWidth / textWidth > 12;
      }
      return false;
    },
    itemsPerPageOptions() {
      return this.contextOverride ? [20, 50, 100, -1] : [20, 50, 100];
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
          this.splitParts.length &&
          (!this.currentPart ||
            !this.splitParts.find((item) => item.id === this.currentPart))
        )
          this.currentPart = this.splitParts[0].id;
      }
      this.updateSize();
      this.loadingParts = false;
    },
    cancelReport() {
      this.cancelTokenSource.cancel("request canceled by user");
    },
    async fetchData() {
      this.loadingData = true;
      this.cancelTokenSource = axios.CancelToken.source();
      let filterOverride = null;
      if (this.contextOverride) {
        filterOverride = {
          date: { start: this.dateRangeStart, end: this.dateRangeEnd },
        };
        if (this.selectedOrganizationId === null) {
          // we do not want to do anything if no org is selected and contextOverride is true
          return;
        }
        if (this.selectedOrganizationId !== -1) {
          filterOverride.organization = [this.selectedOrganizationId];
        }
      }
      let params = {
        ...this.report.urlParams(filterOverride),
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
      this.dataComputing = true;
      await this.updateTranslators();
      if (this.taggableRow) {
        await this.getTagsForObjectsById(
          this.rowToTagScope[this.row],
          this.data.map((item) => item.pk)
        );
      }
      this.recomputeData();
      this.dataComputing = false;
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
      // process the data to translate the primary dimension
      this.cleanData = this.data.map((item) => {
        let newItem = { ...item };
        if (this.translators[this.row]) {
          if (this.row === "tag") {
            // for tags, we translate to whole objects in order to be able
            // to display the tag chip
            newItem[this.row] =
              this.translators[this.row].translateKey(
                newItem.pk ?? newItem[this.row]
              ) ?? null;
          } else {
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
        } else {
          newItem[this.row] = newItem[this.row].toString();
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
    updateSize() {
      this.baseWidth = this.$refs.base.clientWidth;
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
    dateRangeStart() {
      if (this.contextOverride) {
        this.fetchData();
      }
    },
    dateRangeEnd() {
      if (this.contextOverride) {
        this.fetchData();
      }
    },
    selectedOrganizationId() {
      if (this.contextOverride) {
        this.fetchData();
      }
    },
  },
};
</script>
