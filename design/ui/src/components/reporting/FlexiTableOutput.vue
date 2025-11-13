<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<i18n lang="yaml" src="@/locales/errors.yaml"></i18n>

<i18n lang="yaml">
en:
  detail: Detail
  error: Error
  error_code: Error code
  error_intro: The following error was reported during the preparation of the report.
  available_parts: "Split by: {splitby} - {count} available | Split by: {splitby} - {count} available | Split by: {splitby} - {count} available"
  loading_parts: Loading list of parts
  remainder: Remainder without any tags
  no_data: No data matching the current setup was found.
  row_total: Row total
  change: Change
  change_percent: Change %
  pop_out: Expand to full screen
  parts_cropped: There are too many parts ({count}), showing only the first {max}. Note - unless the number of parts is reduced, export will fail.
  no_data_for_chart: No data to display in the chart.
  merge_report_types_tt_primary: Primary report has been used for the data.
  merge_report_types_tt_secondary: Fallback report has been used for the data.
cs:
  detail: Detail
  error: Chyba
  error_code: Kód chyby
  error_intro: Následující chyba byla nahlášena při přípravě požadovaného reportu.
  available_parts: "Rozdělit podle: {splitby} - {count} možnost | Rozdělit podle: {splitby} - {count} možnosti | Rozdělit podle: {splitby} - {count} možností"
  loading_parts: Nahrávám seznam částí
  remainder: Zbytek bez přiřazeného štítku
  no_data: Nebyla nalezena žádná data odpovídající aktuálnímu nastavení.
  row_total: Celkem
  change: Změna
  change_percent: Změna %
  pop_out: Roztáhnout na celou obrazovku
  parts_cropped: Report obsahuje příliš mnoho částí ({count}), zobrazuji pouze prvních {max}. Poznámka - pokud počet částí nesnížíte, export selže.
  no_data_for_chart: Žádná data pro zobrazení v grafu.
  merge_report_types_tt_primary: Hlavní report byl použit pro data.
  merge_report_types_tt_secondary: Záložní report byl použit pro data.
</i18n>

<template>
  <div ref="base" v-resize="updateSize">
    <div v-if="loadingParts">
      <v-progress-linear indeterminate :height="24" class="mb-4">
        <span class="text-caption">{{ $t("loading_parts") }}</span>
      </v-progress-linear>
    </div>
    <div
      v-else-if="
        dataToShow.length ||
        (loading && !errorCode) ||
        (report &&
          report.splitBy &&
          splitParts.length &&
          currentPart !== undefined)
      "
    >
      <!-- part selector -->
      <div class="d-flex py-4 justify-space-between">
        <div v-if="report.splitBy && splitParts.length">
          <OutlinedContainer
            :label="
              $tc('available_parts', {
                count: splitParts.length,
                splitby:
                  report.splitBy.names[$i18n.locale] || $t(report.splitBy.name),
              })
            "
            v-if="partsSideBySide"
            border-color="transparent"
          >
            <v-slide-group v-model="currentPart">
              <v-slide-group-item
                v-for="item in splitParts"
                :key="item.id"
                v-slot="{ isSelected, toggle }"
                :value="item.id"
              >
                <v-btn
                  @click="toggle"
                  :value="isSelected"
                  variant="outlined"
                  class="years_report"
                  tile
                  :class="[isSelected ? 'active-button' : '']"
                  >{{ item.title }}
                </v-btn>
              </v-slide-group-item>
            </v-slide-group>
          </OutlinedContainer>
          <!-- if there are too many parts, use a select -->
          <v-autocomplete
            v-else
            :items="splitParts"
            v-model="currentPart"
            :label="
              $tc('available_parts', {
                count: splitParts.length,
                splitby:
                  report.splitBy.names[$i18n.locale] || $t(report.splitBy.name),
              })
            "
            item-value="id"
            variant="outlined"
            density="compact"
            max-width="450px"
            min-width="370px"
          ></v-autocomplete>
          <v-alert v-if="partsCropped" type="warning" variant="outlined">
            {{
              $t("parts_cropped", {
                count: formatInteger(totalParts),
                max: splitParts.length,
              })
            }}
          </v-alert>
        </div>
        <div v-else></div>
        <div class="ps-4">
          <v-btn-toggle v-model="view" density="compact" variant="outlined">
            <v-btn value="table">
              <v-icon size="small">fa fa-table</v-icon>
            </v-btn>
            <v-btn value="chart">
              <v-icon size="small">fas fa-chart-bar</v-icon>
            </v-btn>
          </v-btn-toggle>
        </div>
      </div>
      <v-skeleton-loader
        type="paragraph@10"
        loading
        class="py-10 px-5"
        v-if="loading"
      ></v-skeleton-loader>
      <v-data-table-server
        v-else-if="view === 'table' && totalRowCount !== null"
        :items="formattedData"
        :headers="tableHeaders"
        item-key="pk"
        :loading="loading"
        :page="page"
        :items-per-page="itemsPerPage"
        :items-length="totalRowCount"
        :fixed-header="popped"
        :height="popped ? 'calc(100vh - 72px)' : null"
        @update:options="updateOptions"
        v-model:sort-by="sortBy"
        :style="
          popped
            ? {
                position: 'fixed',
                top: '8px',
                left: '8px',
                width: 'calc(100vw - 16px)',
                'padding-right': '10px',
                zIndex: 1007,
                boxShadow: '0 0 0 20px rgba(0, 0, 0, 0.7)',
              }
            : {}
        "
      >
        <template #headers="{ columns }">
          <TableCustomSort
            :columns="columns"
            v-model:externalOrderBy="sortBy"
          />
        </template>

        <template #item.tag="{ item }">
          <TagChip :tag="item.tag" show-class small v-if="item.pk"></TagChip>
          <span v-else class="text--secondary">{{ item.tag }}</span>
        </template>

        <!-- create columns for each row that is taggable -->
        <template
          v-for="(row, index) in rows"
          v-slot:[`item.${row}__tags`]="{ item }"
        >
          <template v-if="rowToTagScope[row]">
            <TagChip
              v-for="tag in getTagsForObjectById(
                rowToTagScope[row],
                item[getPkField(index)],
              )"
              :key="tag.pk"
              :tag="tag"
              small
              show-class
            ></TagChip>
          </template>
        </template>

        <template #item.reldiff="{ item }">
          <span>
            {{ formatPercentage(item.reldiff) }}
            <TrendArrow :diff="item.reldiff"></TrendArrow>
          </span>
        </template>

        <template #item.coverage="{ item }">
          <v-progress-circular
            v-if="coverageData[item.pk] === undefined"
            color="grey"
            indeterminate
            size="16"
            width="1"
          ></v-progress-circular>
          <div v-else-if="coverageData[item.pk]">
            <v-progress-linear
              :model-value="Math.round(coverageData[item.pk].ratio * 100)"
              :color="getCoverageColor(coverageData[item.pk].ratio)"
              height="16"
            >
              <template #default="{ value }">
                <strong class="text-white text-caption"
                  >{{ Math.round(value) }}%</strong
                >
              </template>
            </v-progress-linear>
          </div>
          <div v-else class="text-center text-grey">
            <span class="text-caption">{{ $t("no_data") }}</span>
          </div>
        </template>

        <template #item.used_rts="{ item }">
          <v-tooltip
            location="bottom"
            max-width="600px"
            v-for="rt in item.used_rts"
            :key="rt"
          >
            <template #activator="{ props }">
              <span v-bind="props">
                <v-chip
                  size="x-small"
                  class="mr-1"
                  :color="isPrimaryReportType(rt) ? 'primary' : ''"
                  :variant="isPrimaryReportType(rt) ? 'flat' : 'tonal'"
                  >{{ rt }}</v-chip
                >
              </span>
            </template>
            {{
              isPrimaryReportType(rt)
                ? $t("merge_report_types_tt_primary")
                : $t("merge_report_types_tt_secondary")
            }}
          </v-tooltip>
        </template>

        <template
          #body.append="{ columns }"
          v-if="remainderVisible && (remainder || loadingRemainder)"
        >
          <tr>
            <td
              v-for="header in columns"
              :key="header.title"
              style="background-color: #e7e7e7"
              :class="header.value === 'tag' ? 'text--secondary' : 'text-end'"
            >
              <span v-if="header.value === 'tag'">
                {{ $t("remainder") }}
              </span>
              <span v-else-if="loadingRemainder">
                <v-icon size="small">fas fa-spinner fa-spin</v-icon>
              </span>
              <span v-else-if="remainder">
                {{
                  header.type === "float"
                    ? formatPercentage(remainder[header.value])
                    : formatInteger(remainder[header.value])
                }}
                <TrendArrow
                  v-if="header.value === 'reldiff'"
                  :diff="remainder.reldiff"
                ></TrendArrow>
              </span>
            </td>
          </tr>
        </template>

        <template #footer.prepend>
          <v-btn
            @click="togglePopOut"
            variant="text"
            size="small"
            color="secondary"
            id="popOutButton"
            class="expand_full_button"
          >
            <v-icon size="small" class="mr-2">{{
              popped ? "fa fa-times" : "fas fa-external-link-alt"
            }}</v-icon>
            {{ popped ? $t("close") : $t("pop_out") }}
          </v-btn>
        </template>
      </v-data-table-server>

      <div v-else-if="view === 'chart' && !loading">
        <ReportingChart
          v-if="totalRowCount"
          :data="dataWithRemainder"
          :primary-dimensions="rows"
          :series="chartSeries"
          :type="
            rows.length && rows[0].startsWith('date') ? 'histogram' : 'bar'
          "
          :height="
            (rows.length && rows[0].startsWith('date')
              ? 480
              : 260 + dataToShow.length * 20) + 'px'
          "
        ></ReportingChart>
        <v-alert v-else type="info" variant="outlined">
          {{ $t("no_data_for_chart") }}
        </v-alert>
      </div>
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
      <v-alert type="info" variant="outlined">{{ $t("no_data") }}</v-alert>
    </div>
  </div>
</template>

<script>
import ReportingChart from "@/components/reporting/ReportingChart";
import TrendArrow from "@/components/reporting/TrendArrow.vue";
import TableCustomSort from "@/components/tables/TableCustomSort";
import TagChip from "@/components/tags/TagChip";
import OutlinedContainer from "@/components/util/OutlinedContainer.vue";
import { smartMonthRange } from "@/libs/dates";
import { splitGroup } from "@/libs/group-ids";
import { formatInteger } from "@/libs/numbers";
import { toBase64JSON } from "@/libs/serialization";
import { djangoToDataTableOrderBy } from "@/libs/sorting";
import cancellation from "@/mixins/cancellation";
import tags from "@/mixins/tags";
import translators from "@/mixins/translators";
import axios from "axios";
import { isEqual } from "lodash";
import { useGoTo } from "vuetify";
import { mapActions, mapGetters, mapState } from "vuex";

export default {
  name: "FlexiTableOutput",
  components: {
    TrendArrow,
    TagChip,
    ReportingChart,
    TableCustomSort,
    OutlinedContainer,
  },
  mixins: [translators, cancellation, tags],

  props: {
    readonly: { default: false, type: Boolean },
    showRowTotals: { default: false, type: Boolean },
    // if the organization and selected dates should be used from the UI,
    // and not from the report, set this to true
    contextOverrideOrganization: { default: false, type: Boolean },
    contextOverrideDates: { default: false, type: Boolean },
    // in interactive mode, the data is reloaded immediately when the context is changed
    interactiveContextOverride: { default: false, type: Boolean },
  },

  setup() {
    const goTo = useGoTo();
    return { goTo };
  },

  data() {
    return {
      report: null,
      part: null,
      data: [],
      cleanData: [],
      totalRowCount: null,
      loadingData: false,
      loadingRemainder: false,
      dataComputing: false,
      translatorsUpdating: false,
      extractedHeaders: [],
      titleColumns: {
        issn: true,
        eissn: true,
        isbn: true,
        doi: false,
      },
      itemColumns: {
        doi: true,
        issn: true,
        eissn: true,
        isbn: true,
        publication_date: true,
      },
      errorCode: null,
      errorDetails: null,
      cancelTokenSource: null,
      justFetchingParams: null,
      splitParts: [],
      currentPart: undefined,
      loadingParts: false,
      totalParts: 0,
      view: "table",
      page: 1,
      itemsPerPage: 25,
      prevOptions: {},
      sortBy: [{ key: "_total", order: "desc" }],
      ordering: "-_total",
      baseWidth: 0,
      remainder: null,
      rowToTagScope: {
        target: "title",
        platform: "platform",
        organization: "organization",
      },
      popped: false,
      coverageData: {},
    };
  },

  computed: {
    ...mapGetters({
      dateRangeStart: "dateRangeStartText",
      dateRangeEnd: "dateRangeEndText",
      dateRangeExplicitEndText: "dateRangeExplicitEndText",
    }),
    ...mapState({
      selectedOrganizationId: "selectedOrganizationId",
    }),
    loading() {
      return this.loadingData || this.dataComputing || this.translatorsUpdating;
    },
    activeTitleColumns() {
      if (this.rows.includes("target")) {
        return Object.entries(this.titleColumns)
          .filter(([key, value]) => value)
          .map(([key, value]) => key);
      }
      return [];
    },
    activeItemColumns() {
      if (this.rows.includes("item")) {
        return Object.entries(this.itemColumns)
          .filter(([key, value]) => value)
          .map(([key, value]) => key);
      }
      return [];
    },
    headersFromData() {
      if (this.report.trendMode) {
        const baseHeader = smartMonthRange(
          this.report.getEffectiveBaseSubsetDateRange(),
        );
        const comparedHeader = smartMonthRange(
          this.report.getEffectiveComparedSubsetDateRange(),
        );
        return [
          { title: baseHeader, value: "base", align: "end" },
          {
            title: comparedHeader,
            value: "compared",
            align: "end",
          },
          { title: this.$t("change"), value: "diff", align: "end" },
          {
            title: this.$t("change_percent"),
            value: "reldiff",
            align: "end",
            type: "float",
          },
        ];
      }
      return this.extractedHeaders;
    },
    tableHeaders() {
      if (this.report) {
        let headers = [];
        if (
          (this.showRowTotals || this.report?.includeTotals) &&
          !this.report.trendMode
        ) {
          headers.push({
            title: this.$t("row_total"),
            value: "_total",
            sortable: true,
            align: "end",
            order: "reverse",
          });
        }
        this.headersFromData.forEach((item) =>
          headers.push({
            ...item,
            sortable: !this.readonly,
            headerProps: {
              class: "data-col",
            },
            cellProps: {
              class: "data-col",
            },
            order: "reverse",
            sortRaw(a, b) {
              if (
                Number(a[item.value].replace(/\s/g, "")) <
                Number(b[item.value].replace(/\s/g, ""))
              )
                return -1;
              if (
                Number(a[item.value].replace(/\s/g, "")) >
                Number(b[item.value].replace(/\s/g, ""))
              )
                return 1;
            },
          }),
        );
        let titleHeaders = this.activeTitleColumns.map((key) => ({
          title: this.$t("title_fields." + key),
          value: "target__" + key,
          order: "reverse",
        }));
        let itemHeaders = this.activeItemColumns.map((key) => ({
          title: this.$t("title_fields." + key),
          value: "item__" + key,
        }));
        let coverageHeaders = this.showCoverageColumn
          ? [
              {
                title: this.$t("labels.coverage"),
                value: "coverage",
                sortable: false,
                align: "center",
                width: "100px",
              },
            ]
          : [];
        // Handle multiple primary dimensions
        let primaryDimensionHeaders = [];
        this.report.effectivePrimaryDimensions.forEach((dim, index) => {
          primaryDimensionHeaders.push({
            title: dim.getName(this.$i18n),
            value: dim.ref,
            sortable: !this.readonly,
          });
          // push title headers immediately after the title main dimension
          if (dim.ref === "target") {
            primaryDimensionHeaders.push(...titleHeaders);
          }
          // push item headers immediately after the item main dimension
          if (dim.ref === "item") {
            primaryDimensionHeaders.push(...itemHeaders);
          }
          // check if this is a taggable column and add the tags column
          if (this.rowToTagScope[dim.ref]) {
            primaryDimensionHeaders.push({
              title: this.$t(`labels.tags_${this.rowToTagScope[dim.ref]}`),
              value: dim.ref + "__tags",
              sortable: this.report.tagRollUp,
            });
          }
        });

        let ret = [...primaryDimensionHeaders, ...coverageHeaders, ...headers];
        return ret;
      }
      return [];
    },
    rows() {
      // Return all primary dimensions for multiindex support
      if (this.report?.primaryDimensions?.length > 0) {
        return this.report.primaryDimensions.map((dim) => dim.ref);
      }
      return [this.report?.effectivePrimaryDimension?.ref].filter(Boolean);
    },
    usesMultiIndex() {
      return this.report?.primaryDimensions?.length > 1;
    },
    dataUrl() {
      return "/api/flexible-slicer/";
    },
    errorText() {
      if (this.errorCode) {
        return this.$t(this.errorCode, this.errorDetails);
      }
      return "";
    },
    chartSeries() {
      let headers = this.headersFromData;
      if (this.report.trendMode) {
        headers = headers.filter(
          (item) => item.value !== "diff" && item.value !== "reldiff",
        );
      }
      return Object.fromEntries(
        headers.map((item) => [item.value, item.title]),
      );
    },
    formattedData() {
      return this.dataToShow.map((item) => {
        let newItem = { ...item };
        for (let key of Object.keys(newItem)) {
          const header = this.tableHeaders.find((item) => item.value === key);
          if (header?.align === "end" && header?.type !== "float") {
            newItem[key] = formatInteger(newItem[key]);
          }
        }
        return newItem;
      });
    },
    dataToShow() {
      return this.cleanData;
    },
    dataWithRemainder() {
      if (this.remainder) {
        return [
          ...this.dataToShow,
          { ...this.remainder, tag: this.$t("remainder") },
        ];
      }
      return this.dataToShow;
    },
    partsSideBySide() {
      if (this.baseWidth && this.splitParts.length) {
        const textWidth = this.splitParts.reduce(
          (acc, item) => acc + item.title.length,
          0,
        );
        return this.baseWidth / textWidth > 14;
      }
      return false;
    },
    remainderVisible() {
      if (this.usesMultiIndex) return false;
      return this.rows[0] === "tag" && this.report.showUntaggedRemainder;
    },
    contextOverride() {
      return this.contextOverrideOrganization || this.contextOverrideDates;
    },
    noPartAvailable() {
      return (
        this.report.splitBy &&
        this.currentPart === undefined &&
        !this.loadingParts
      );
    },
    partsCropped() {
      return this.totalParts > this.splitParts.length;
    },
    showCoverageColumn() {
      return (
        !this.usesMultiIndex &&
        this.rows[0] === "platform" &&
        !this.report.trendMode
      );
    },
  },

  methods: {
    ...mapActions(["showSnackbar"]),
    formatInteger,
    async updateOutput(report) {
      this.report = report;

      // if we are in the split mode, we need to check the possible splits first
      this.splitParts = [];
      if (this.report.splitBy) {
        let partsOk = await this.getSplitParts();
        if (!partsOk) {
          return;
        }
      } else {
        this.currentPart = undefined;
      }

      if (this.noPartAvailable) {
        // we cannot show the report without a part, so we just return
        return;
      }

      // update translators
      this.report.groupBy
        .filter((item) => item.isExplicit)
        .forEach((item) => {
          this.translators[item.ref] = this.getTranslator(item);
        });

      // Set up translators for all primary dimensions
      this.report.primaryDimensions.forEach((dim) => {
        this.translators[dim.ref] = this.getTranslator(dim);
      });

      this.errorCode = null;
      this.errorDetails = null;

      // clear the data
      this.data = [];
      this.cleanData = [];
      this.setOrdering(report);

      await this.fetchData();
    },
    async getSplitParts() {
      this.loadingParts = true;
      let resp = await this.http({
        url: "/api/flexible-slicer/parts/",
        params: this.report.urlParams(),
        dontShowError: true,
      });
      if (resp.error) {
        // deal with the error and return false
        if (resp.error.code) {
          let code = resp.error.code;
          this.showError(code, resp.error.message);
        } else {
          this.showSnackbar({
            content: "Could not load data: " + error,
            color: "error",
          });
        }
        this.loadingParts = false;
        return false;
      }
      if (resp.response) {
        this.totalParts = resp.response.data.count;
        let splitParts = resp.response.data.values.map(
          (item) => item[this.report.splitBy.ref],
        );
        const translator = this.getTranslator(this.report.splitBy);
        if (translator) {
          await translator.prepareTranslation(splitParts);
          this.splitParts = splitParts
            .map((item) => {
              return {
                id: item,
                title: translator.translateKeyToString(item, this.$i18n.locale),
              };
            })
            .sort((a, b) => {
              if (a.id === null) {
                a.title = this.$t("labels.empty_value");
              }
              if (b.id === null) {
                b.title = this.$t("labels.empty_value");
              }
              return a.title.localeCompare(b.title);
            });
        } else {
          this.splitParts = splitParts.map((item) => {
            return { id: item, title: item.toString() };
          });
        }
        this.splitParts.sort((a, b) => {
          if (a.id === null) {
            a.title = this.$t("labels.empty_value");
          }
          if (b.id === null) {
            b.title = this.$t("labels.empty_value");
          }
          return a.title.localeCompare(b.title);
        });
        if (
          this.splitParts.length &&
          (this.currentPart === undefined ||
            !this.splitParts.find((item) => item.id === this.currentPart))
        ) {
          this.currentPart = this.splitParts[0].id;
        }
      }
      this.updateSize();
      this.loadingParts = false;
      return true;
    },
    cancelReport() {
      this.cancelTokenSource.cancel("request canceled by user");
    },
    async fetchData() {
      if (!this.report) return;
      this.remainder = null;
      let params = {
        ...this.report.urlParams(),
        page_size: this.itemsPerPage,
        page: this.page,
        order_by: this.ordering,
      };
      if (this.report.splitBy && this.currentPart !== undefined) {
        params["part"] = toBase64JSON([this.currentPart]);
      }

      // check if a request is already in progress and if it is for different
      // parameters or for the same ones
      // - if it is for different parameters, we cancel the previous request
      // - if it is for the same parameters, we do nothing
      //
      // BTW, we need this because the report may be fetched twice
      // - once explicitly by user pressing a button
      // - once implicitly by the watcher on the report properties
      if (this.cancelTokenSource) {
        if (!isEqual(params, this.justFetchingParams)) {
          this.cancelTokenSource.cancel("request cancelled by newer request");
        } else {
          // this request is already in progress, so we do nothing
          console.log("request already in progress, skipping");
          return;
        }
      }

      // start fetching data
      this.loadingData = true;
      this.cancelTokenSource = axios.CancelToken.source();
      this.justFetchingParams = { ...params };
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
          console.debug("Cancelled request: ", error.message);
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
        this.justFetchingParams = null;
      }
      // post-processing
      this.dataComputing = true;
      await this.updateTranslators();
      for (const [idx, row] of this.rows.entries()) {
        if (this.rowToTagScope[row]) {
          this.cleanTagCache(this.rowToTagScope[row]); // clear the cache because taggings may have changed
          await this.fetchTagsForObjectsById(
            // fix for multiindex, for now tagging is disabled in multiindex mode
            this.rowToTagScope[row],
            this.data.map((item) => item[this.getPkField(idx)]),
          );
        }
      }
      this.recomputeData();
      this.dataComputing = false;

      if (this.showCoverageColumn) {
        this.fetchCoverageForPlatforms();
      }

      // remainder
      if (this.remainderVisible) {
        this.loadingRemainder = true;
        try {
          let resp = await axios.get(this.dataUrl + "remainder/", {
            params: params,
          });
          this.remainder = resp.data;
        } catch (error) {
          this.showSnackbar({
            content: "Could not load remainder: " + error,
            color: "error",
          });
        } finally {
          this.loadingRemainder = false;
        }
      }
    },
    getPkField(index) {
      return index === 0 ? "pk" : `pk${index + 1}`;
    },
    async updateTranslators() {
      this.translatorsUpdating = true;
      let promises = [];

      // update translators for all primary dimensions
      this.report.primaryDimensions.forEach((dim, index) => {
        const pkField = this.getPkField(index);
        const dimRef = dim.ref;

        if (this.translators[dimRef]) {
          // All primary dimensions now use pk, pk2, pk3, etc. keys consistently
          let pks = this.data.map((item) => item[pkField]);
          promises.push(this.translators[dimRef].prepareTranslation(pks));
        }
      });

      // update translators for all dimensions from the data which are not primary dimensions
      if (this.data.length > 0) {
        // Get all primary dimension fields to exclude them
        let primaryDimFields = [];
        for (let i = 0; i < this.report.primaryDimensions.length; i++) {
          primaryDimFields.push(this.getPkField(i));
        }

        let pks_lists = Object.keys(this.data[0])
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
      // if mergeReportTypes is active, we need to translate the report types from ids to names
      if (this.report.mergeReportTypes) {
        let rt_ids = [];
        this.data.forEach((item) => {
          for (let rt of item.used_rts) {
            if (!rt_ids.includes(rt)) {
              rt_ids.push(rt);
            }
          }
        });
        await this.translators["report_type"].prepareTranslation(rt_ids);
      }
      this.translatorsUpdating = false;
    },
    recomputeData() {
      // process the data to translate the primary dimensions
      this.cleanData = this.data.map((item) => {
        let newItem = { ...item };

        for (const [index, row] of this.rows.entries()) {
          const pkField = this.getPkField(index);

          if (this.translators[row]) {
            if (row === "tag") {
              // for tags, we translate to whole objects in order to be able
              // to display the tag chip
              newItem[row] =
                this.translators[row].translateKey(newItem[pkField]) ?? null;
            } else {
              newItem[row] =
                this.translators[row].translateKeyToString(
                  newItem[pkField],
                  this.$i18n.locale,
                ) ?? this.$t("blank_value");
              if (row === "target") {
                // extra data for titles
                let obj = this.translators[row].translateKey(newItem[pkField]);
                if (obj) {
                  Object.keys(this.titleColumns).forEach((key) => {
                    newItem["target__" + key] = obj[key];
                  });
                }
              }
              if (row === "item") {
                let obj = this.translators[row].translateKey(newItem[pkField]);
                if (obj) {
                  Object.keys(this.itemColumns).forEach((key) => {
                    newItem["item__" + key] = obj[key];
                  });
                }
              }
            }
          } else {
            newItem[row] = newItem[pkField].toString();
          }
        }

        return newItem;
      });
      // extract the header row data
      let extractedHeaders = [];
      if (this.data.length > 0) {
        for (let key of Object.keys(this.data[0]).filter(
          (item) => item.substr(0, 4) === "grp-",
        )) {
          let pks = splitGroup(key);
          let texts = [];
          let i = 0;
          for (let group of this.report.groupBy) {
            if (this.translators[group.ref]) {
              texts.push(
                this.translators[group.ref].translateKeyToString(
                  pks[i],
                  this.$i18n.locale,
                ) ?? "-",
              );
            } else {
              let value = pks[i];
              if (group.ref.startsWith("date") && value) {
                if (String(value).match(/^\d{4}-\d{2}-\d{2}$/)) {
                  value = value.substring(0, 7);
                }
              }
              texts.push(value);
            }
            i++;
          }
          let text = texts.join(" / ");
          extractedHeaders.push({ title: text, value: key, align: "end" });
        }
      }
      this.extractedHeaders = extractedHeaders.sort((a, b) =>
        a.title.localeCompare(b.title),
      );
      // if mergeReportTypes is active, we add a column with the used report types
      // we need to translate the report types from ids to names
      if (this.report.mergeReportTypes) {
        this.cleanData.forEach((item) => {
          item.used_rts = item.used_rts.map((rt) =>
            this.translators["report_type"].translateKeyToString(
              rt,
              this.$i18n.locale,
            ),
          );
        });
        this.extractedHeaders.push({
          title: "Used report types",
          value: "used_rts",
        });
      }
    },
    showError(code, details) {
      this.errorCode = code;
      this.errorDetails = details;
    },
    setOrdering(report) {
      // if the report has order by, we use it, otherwise we set a default ordering
      if (report.orderBy && report.orderBy.length) {
        this.sortBy = djangoToDataTableOrderBy(report.orderBy);
        // set ordering immediately, otherwise it would be done after the
        // table calls updateOptions, which would cause inconsistency
        // in the fetchData call immediately after setOrdering and cause double loading of data
        this.ordering = report.orderBy[0];
      } else {
        this.sortBy = [{ key: "_total", order: "desc" }];
      }
    },
    updateSize() {
      this.baseWidth = this.$refs.base.clientWidth;
    },
    formatPercentage(number) {
      if (number === null) {
        return "∞%";
      }
      return number.toLocaleString(this.$i18n.locale, {
        style: "percent",
        minimumFractionDigits: 1,
        maximumFractionDigits: 1,
      });
    },
    togglePopOut() {
      this.popped = !this.popped;
      if (!this.popped) {
        this.$nextTick(() =>
          // scroll to the bottom where the button is
          // this returns the user to where he popped out from which seems
          // to be the most intuitive - by default he would end up on top
          // of the page which is confusing
          this.goTo("#popOutButton", { duration: 0 }),
        );
      }
    },

    updateOptions(newOptions) {
      if (!isEqual(newOptions, this.prevOptions)) {
        let change = false;

        if (this.page !== newOptions.page) {
          this.page = newOptions.page;
          change = true;
        }

        if (this.itemsPerPage !== newOptions.itemsPerPage) {
          this.itemsPerPage = newOptions.itemsPerPage;
          change = true;
        }

        let newOrdering = "-_total"; // default ordering
        if (newOptions.sortBy && newOptions.sortBy.length) {
          newOrdering = newOptions.sortBy
            .map(({ key, order }) => {
              return (order === "desc" ? "-" : "") + key;
            })
            .join("");
        }
        if (newOrdering !== this.ordering) {
          this.ordering = newOrdering;
          change = true;
        }

        if (change) {
          this.$emit("update:ordering", this.ordering);
          if (!this.loading) {
            this.fetchData();
          }
        }
      }
      this.prevOptions = { ...newOptions };
    },

    applyOverridesToReport() {
      if (this.report) {
        if (this.contextOverrideDates) {
          this.report.setDateOverride(
            this.dateRangeStart,
            this.dateRangeExplicitEndText,
          );
        } else {
          this.report.clearDateOverride();
        }
        if (this.contextOverrideOrganization) {
          this.report.setOrganizationOverride(
            this.selectedOrganizationId > 0
              ? this.selectedOrganizationId
              : undefined,
          );
        } else {
          this.report.clearOrganizationOverride();
        }
      }
    },
    getCoverageColor(value) {
      const hue = value * value * value * 120;
      return `hsl(${hue}, 50%, 50%)`;
    },
    async fetchCoverageForPlatforms() {
      if (!this.cleanData.length) {
        return;
      }

      this.coverageData = {};
      const baseParams = this.report.urlParams();

      for (const platformRow of this.cleanData) {
        const platformId = platformRow.pk;
        const resp = axios
          .get("/api/flexible-slicer/coverage/", {
            params: {
              ...baseParams,
              filters: toBase64JSON({
                ...JSON.parse(atob(baseParams.filters)),
                platform: [platformId],
              }),
            },
          })
          .then((resp) => {
            if (resp.data && resp.data.overall) {
              this.coverageData[platformId] = resp.data.overall;
            } else {
              this.coverageData[platformId] = null;
            }
          })
          .catch((error) => {
            console.warn(
              `Failed to fetch coverage for platform ${platformId}:`,
              error,
            );
            this.coverageData[platformId] = null;
          });
      }
    },
    isPrimaryReportType(rt) {
      return (
        this.report.reportTypes.findIndex((item) => item.name === rt) === 0
      );
    },
  },
  watch: {
    showRowTotals(newVal) {
      if (this.report) {
        if (newVal) {
          this.report.includeTotals = true;
        } else {
          this.report.includeTotals = false;
        }
      }
    },
    currentPart() {
      this.fetchData();
    },
    dateRangeStart() {
      this.applyOverridesToReport();
      if (this.interactiveContextOverride) {
        this.fetchData();
      }
    },
    dateRangeEnd() {
      this.applyOverridesToReport();
      if (this.interactiveContextOverride) {
        this.fetchData();
      }
    },
    selectedOrganizationId() {
      this.applyOverridesToReport();
      if (this.interactiveContextOverride) {
        this.fetchData();
      }
    },
    contextOverrideDates() {
      this.applyOverridesToReport();
      if (this.interactiveContextOverride) {
        this.fetchData();
      }
    },
    contextOverrideOrganization() {
      this.applyOverridesToReport();
      if (this.interactiveContextOverride) {
        this.fetchData();
      }
    },
    report() {
      this.applyOverridesToReport();
    },
  },
};
</script>

<style lang="scss" scoped>
:deep(.data-col) {
  background-color: #f5f5f5;
  color: rgba(0, 0, 0, 0.6);
}

:deep(tr:hover td.data-col) {
  background-color: #e0e0e0;
}

:deep(.v-data-table__tr) {
  height: 32px;
}

.expand_full_button {
  margin-right: auto;
}

.years_report {
  border: 1px solid #00000020;
}

.active-button {
  background-color: #00000020;
  border: 1px solid #2b2b2b10;
}
:deep(.v-progress-linear__background) {
  opacity: 0.4 !important;
}
</style>
