<i18n lang="yaml" src="@/locales/common.yaml" />
<i18n lang="yaml" src="@/locales/dialog.yaml" />
<i18n lang="yaml" src="@/locales/reporting.yaml" />
<i18n lang="yaml">
en:
  run_report: Run report
  cancel_report: Cancel report
  run_export: Export
  not_empty: This field cannot be empty
  column_order_tt: This number shows the position which this dimension will occupy in the column header. It is based on the order in which the checkboxes are checked.
  download_on_separate_page: You can find all exports on the {exports_page} page.
  select_report_type: First select at least one report type.
  unlock_tt: Unlock the report for editing.
  save_success: Report was successfully saved.
  report_title: Report title
  please_fill_in_title: Please fill in report title and access level and hit 'Save changes' again.
  select_at_least_one_column_dim: At least one column dimension must be selected.
  split_to_parts: Split report to parts by selected attribute
  dont_split: "-- no splitting --"
  title_tags: Tags for title filtering
  title_tags_tt: |
    Tags are used to simplify filtering of titles. You can add tags to individual titles on their corresponding pages
    or in one batch by uploading a title list.
  organization_tags: Tags for organization filtering
  platform_tags: Tags for platform filtering
  tag_class_filter: Limit returned tags by tag class
  no_tag_class_filter: Allow all tag classes
  no_tags_present: There are no tags available for the selected rows.
  organization_count_tt: |
    The number of organizations you have access to. Without an organization filter, the report will be run for all
    these organizations.

cs:
  run_report: Spustit report
  cancel_report: Zrušit report
  run_export: Exportovat
  not_empty: Toto pole nesmí být prázdné
  detail: Detail
  column_order_tt: Toto číslo ukazuje pořadí v jakém bude tento rozměr uveden v hlavičce sloupců. Číslo je dané pořadím v jakém byla políčka zaškrtnuta.
  download_on_separate_page: Všechny exporty najdete na stránce {exports_page}.
  select_report_type: Nejprve vyberte alespoň jeden typ reportu.
  unlock_tt: Odemknout report pro editaci.
  save_success: Report byl úspěšně uložen.
  report_title: Název reportu
  please_fill_in_title: Vyplňte prosím název reportu a úroveň přístupu výše a pak stiskněte tlačítko 'Uložit změny' znovu.
  select_at_least_one_column_dim: Musí být vybrán alespoň jeden rozměr, který definuje sloupce.
  split_to_parts: Rozdělit report na části podle vybraného atributu
  dont_split: "-- nedělit --"
  title_tags: Štítky pro filtrování titulů
  title_tags_tt: |
    Pro zjednodušení filtrování titulů jsou použity štítky. Můžete je k titulům přidávat na stránce daného titulu nebo
    nahrát celý titulový seznam ze souboru.
  platform_tags: Štítky pro filtrování platforem
  organization_tags: Štítky pro filtrování organizací
  tag_class_filter: Omezit štítky na vybraný typ
  no_tag_class_filter: Použít všchny typy štítků
  no_tags_present: Pro zvolené řádky nejsou k dispozici žádné štítky.
  organization_count_tt: |
    Počet organizací, ke kterým máte přístup. Bez filtru organizací bude report spuštěn pro všechny tyto organizace.
</i18n>

<template>
  <v-container fluid>
    <ReportLoadingWidget v-if="loading" />
    <div v-else>
      <v-form v-model="headerFormValid">
        <v-row v-if="wantsSave">
          <v-col cols="12" md="8">
            <h2 class="font-weight-light text-h5 pt-4" v-if="readOnly">
              {{ reportName }}
            </h2>
            <v-text-field
              v-else
              v-model="reportName"
              class="font-weight-light text-h5"
              :label="$t('report_title')"
              :rules="wantsSave ? [rules.required] : []"
              ref="titleField"
            />
          </v-col>
          <v-col>
            <AccessLevelSelector
              :value="accessLevel"
              ref="accessLevel"
              :owner-organization="ownerOrganization"
              :disabled="readOnly"
              @change="updateAccessLevel"
            />
          </v-col>
        </v-row>
      </v-form>
      <v-form v-model="formValid">
        <v-row>
          <v-col class="d-flex">
            <v-autocomplete
              v-model="selectedReportTypes"
              :items="allReportTypes"
              :rules="[ruleNotEmpty]"
              :label="$t('labels.report_type')"
              item-value="pk"
              item-text="name"
              multiple
              chips
              deletable-chips
              :disabled="readOnly"
            />
          </v-col>
          <v-col
            class="align-self-center"
            v-if="selectedReportTypes.length === 0"
          >
            <span>
              <v-icon class="pr-2" color="orange"
                >fa fa-angle-double-left</v-icon
              >
              {{ $t("select_report_type") }}
            </span>
          </v-col>
          <v-col class="align-self-end">
            <v-select
              v-model="splitBy"
              :label="$t('split_to_parts')"
              :items="[{ id: null, name: $t('dont_split') }, ...possibleRows]"
              item-text="name"
              item-value="id"
              :disabled="readOnly"
            ></v-select>
          </v-col>
          <v-col
            v-if="readOnly && canEdit"
            cols="auto"
            class="align-self-center"
          >
            <v-tooltip bottom>
              <template #activator="{ on }">
                <v-btn
                  elevation="2"
                  fab
                  small
                  color="primary"
                  @click="edit = true"
                  v-on="on"
                >
                  <v-icon small>fa fa-edit</v-icon>
                </v-btn>
              </template>
              {{ $t("unlock_tt") }}
            </v-tooltip>
          </v-col>
        </v-row>

        <v-row>
          <v-col>
            <v-card class="pa-2">
              <v-card-title class="pt-2">{{ $t("labels.rows") }}</v-card-title>
              <v-card-text>
                <v-radio-group
                  v-model="watchedRow"
                  hide-details
                  class="mt-1"
                  :disabled="!reportTypeSelected || readOnly"
                >
                  <v-radio
                    v-for="row in possibleRows"
                    :label="row.name"
                    :value="row.id"
                    :key="row.id"
                    :disabled="row.id === splitBy"
                  ></v-radio>
                </v-radio-group>
              </v-card-text>
            </v-card>
          </v-col>

          <v-col>
            <v-card class="pa-2">
              <v-card-title class="pt-2">{{
                $t("labels.columns")
              }}</v-card-title>
              <v-card-text>
                <v-checkbox
                  v-for="item in possibleRows"
                  v-model="columns"
                  :label="item.name"
                  :value="item.id"
                  dense
                  hide-details
                  class="mt-1"
                  :disabled="
                    item.id === row ||
                    item.id === splitBy ||
                    !reportTypeSelected ||
                    readOnly ||
                    (item.id === 'date' && columns.includes('date__year')) ||
                    (item.id === 'date__year' && columns.includes('date'))
                  "
                  :key="item.id"
                >
                  <template #append v-if="columns.includes(item.id)">
                    <v-tooltip bottom max-width="320px">
                      <template #activator="{ on }">
                        <v-chip small outlined color="secondary" v-on="on"
                          >{{ columns.indexOf(item.id) + 1 }}
                        </v-chip>
                      </template>
                      {{ $t("column_order_tt") }}
                    </v-tooltip>
                  </template>
                </v-checkbox>
              </v-card-text>
            </v-card>
          </v-col>

          <v-col>
            <v-card class="pa-2">
              <v-card-title class="pt-2">{{
                $t("labels.filters")
              }}</v-card-title>
              <v-card-text>
                <div v-for="row in possibleRows" :key="row.id">
                  <v-checkbox
                    v-model="filters"
                    :label="row.name"
                    :value="row.id"
                    dense
                    hide-details
                    class="mt-1"
                    :disabled="
                      (row.id === 'date' && filters.includes('date__year')) ||
                      (row.id === 'date__year' && filters.includes('date')) ||
                      !reportTypeSelected ||
                      readOnly
                    "
                  >
                    <template #label>
                      {{ row.name }}

                      <v-tooltip
                        bottom
                        v-if="
                          row.id === 'organization' && organizationCount > 1
                        "
                      >
                        <template #activator="{ on }">
                          <v-chip small class="ms-2" v-on="on"
                            >{{ organizationCount }}
                          </v-chip>
                        </template>
                        {{ $t("organization_count_tt") }}
                      </v-tooltip>
                    </template>
                  </v-checkbox>
                </div>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>

        <v-row v-if="tagRollUpPossible">
          <v-col>
            <v-card class="pa-2">
              <v-card-title class="pt-2 float-left">{{
                $t("labels.tags")
              }}</v-card-title>
              <v-card-text class="pt-1">
                <v-row class="align-baseline">
                  <v-col cols="auto" md="3" lg="auto" sm="5">
                    <v-checkbox
                      v-model="tagRollUp"
                      :label="$t('labels.tag_roll_up')"
                      dense
                      class="mt-1"
                      :disabled="
                        !reportTypeSelected || readOnly || !anyAccessibleTag
                      "
                      :hint="!anyAccessibleTag ? $t('no_tags_present') : ''"
                      persistent-hint
                      :hide-details="anyAccessibleTag"
                    >
                    </v-checkbox>
                  </v-col>
                  <v-col md="6" lg="4" sm="7">
                    <TagClassSelector
                      v-if="tagRollUp"
                      :scope="tagScope"
                      v-model="selectedTagClass"
                      :label="$t('tag_class_filter')"
                      :placeholder="$t('no_tag_class_filter')"
                      clearable
                      class="ps-8 pt-4 pe-8"
                      :disabled="readOnly"
                      with-visible-tags
                    />
                  </v-col>
                  <v-col cols="auto" md="3" lg="auto">
                    <v-tooltip bottom v-if="tagRollUp">
                      <template #activator="{ on }">
                        <span v-on="on">
                          <v-checkbox
                            v-model="showRemainder"
                            :label="$t('tags_show_remainder')"
                            :disabled="readOnly"
                            dense
                            hide-details
                            class="mt-1"
                          />
                        </span>
                      </template>
                      {{ $t("tags_show_remainder_tt") }}
                    </v-tooltip>
                  </v-col>
                </v-row>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>

        <v-row v-if="filters.length">
          <v-col>
            <v-card>
              <v-card-title>{{ $t("labels.filter_settings") }}</v-card-title>
              <v-card-text>
                <v-container fluid>
                  <v-row align="start">
                    <!-- organization -->
                    <v-col
                      cols="12"
                      md="6"
                      xl="3"
                      v-if="filters.includes('organization')"
                    >
                      <DimensionKeySelector
                        :query-url="selectorBaseUrl"
                        v-model="selectedOrganizations"
                        dimension="organization"
                        :translator="translators.organization"
                        :name="$t('labels.organization')"
                        :disabled="disableDimValuesSelectors"
                        :read-only="readOnly"
                      />
                    </v-col>
                    <v-col
                      cols="12"
                      md="6"
                      xl="3"
                      v-if="filters.includes('organization')"
                    >
                      <TagSelector
                        scope="organization"
                        v-model="selectedOrganizationTags"
                        :disabled="disableDimValuesSelectors || readOnly"
                        :label="$t('organization_tags')"
                        dont-check-exclusive
                      />
                    </v-col>

                    <!-- platform -->
                    <v-col
                      cols="12"
                      md="6"
                      xl="3"
                      v-if="filters.includes('platform')"
                    >
                      <DimensionKeySelector
                        :query-url="selectorBaseUrl"
                        v-model="selectedPlatforms"
                        dimension="platform"
                        :translator="translators.platform"
                        :name="$t('labels.platform')"
                        :disabled="disableDimValuesSelectors"
                        :read-only="readOnly"
                      />
                    </v-col>
                    <v-col
                      cols="12"
                      md="6"
                      xl="3"
                      v-if="filters.includes('platform')"
                    >
                      <TagSelector
                        scope="platform"
                        v-model="selectedPlatformTags"
                        :disabled="disableDimValuesSelectors || readOnly"
                        :label="$t('platform_tags')"
                        dont-check-exclusive
                      />
                    </v-col>

                    <v-col
                      cols="12"
                      md="6"
                      xl="4"
                      class="d-flex"
                      v-if="filters.includes('target') && enableTags"
                    >
                      <TagSelector
                        scope="title"
                        v-model="selectedTitleTags"
                        :disabled="disableDimValuesSelectors || readOnly"
                        :label="$t('title_tags')"
                        :tooltip="$t('title_tags_tt')"
                        dont-check-exclusive
                      />
                    </v-col>

                    <v-col
                      cols="12"
                      md="6"
                      xl="4"
                      class="d-flex"
                      v-if="filters.includes('metric')"
                    >
                      <DimensionKeySelector
                        :query-url="selectorBaseUrl"
                        v-model="selectedMetrics"
                        dimension="metric"
                        :translator="translators.metric"
                        :name="$t('labels.metric')"
                        :disabled="disableDimValuesSelectors"
                        :read-only="readOnly"
                      />
                    </v-col>

                    <template v-for="(ed, index) in explicitDims">
                      <v-col
                        :key="index"
                        class="d-flex"
                        cols="12"
                        md="6"
                        xl="4"
                        v-if="filters.includes(`dim${index + 1}`)"
                      >
                        <DimensionKeySelector
                          :query-url="selectorBaseUrl"
                          v-model="selectedDimValues[index]"
                          :dimension="`dim${index + 1}`"
                          :name="ed.name"
                          :translator="translators.explicitDimension"
                          :disabled="disableDimValuesSelectors"
                          :read-only="readOnly"
                        />
                      </v-col>
                    </template>

                    <v-col v-if="filters.includes('date')" cols="auto">
                      <FromToMonthEntry
                        v-model="selectedDateRange"
                        :disabled="readOnly"
                      />
                    </v-col>
                    <v-col
                      v-else-if="filters.includes('date__year')"
                      cols="auto"
                    >
                      <FromToYearEntry
                        v-model="selectedDateRange"
                        :disabled="readOnly"
                      />
                    </v-col>
                  </v-row>
                </v-container>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>

        <v-row>
          <v-col v-if="!reportRunning" cols="auto">
            <v-tooltip bottom>
              <template #activator="{ on }">
                <v-btn
                  @click="runReport"
                  :disabled="!(formValid && hasGroupBy) || reportRunning"
                  v-on="on"
                  min-width="12rem"
                >
                  <v-icon small color="green lighten-2" class="mr-1"
                    >fa fa-play
                  </v-icon>
                  {{ $t("run_report") }}
                </v-btn>
              </template>
              {{ $t("run_report_tt") }}
            </v-tooltip>
          </v-col>
          <v-col v-if="reportRunning" cols="auto">
            <v-tooltip bottom>
              <template #activator="{ on }">
                <v-btn
                  @click="cancelReport"
                  :disabled="!(hasGroupBy && reportRunning)"
                  v-on="on"
                  min-width="12rem"
                >
                  <v-icon small color="red lighten-2" class="mr-1"
                    >fa-stop
                  </v-icon>
                  {{ $t("cancel_report") }}
                </v-btn>
              </template>
              {{ $t("cancel_report_tt") }}
            </v-tooltip>
          </v-col>
          <v-col cols="auto">
            <v-menu offset-y class="mb-3">
              <template v-slot:activator="{ on }">
                <v-btn v-on="on" :disabled="!(formValid && hasGroupBy)">
                  <v-icon small color="blue lighten-2" class="mr-1"
                    >fas fa-file-export
                  </v-icon>
                  {{ $t("run_export") }}
                </v-btn>
              </template>
              <v-list>
                <v-list-item @click="runExport('xlsx')">
                  <v-list-item-title>{{
                    $t("format.excel")
                  }}</v-list-item-title>
                </v-list-item>
                <v-list-item @click="runExport('csv')">
                  <v-list-item-title>{{ $t("format.csv") }}</v-list-item-title>
                </v-list-item>
              </v-list>
            </v-menu>
          </v-col>
          <v-col cols="auto">
            <ExportMonitorWidget
              v-if="exportHandle"
              :export-id="exportHandle.pk"
            />
            <v-alert v-else-if="exportHint" type="info" outlined dismissible>
              <i18n path="download_on_separate_page">
                <template #exports_page>
                  <router-link :to="{ name: 'exports' }">{{
                    $t("pages.exports")
                  }}</router-link>
                </template>
              </i18n>
            </v-alert>
          </v-col>
          <v-col cols="auto">
            <v-alert
              type="warning"
              v-if="!hasGroupBy && selectedReportTypes.length"
              outlined
              >{{ $t("select_at_least_one_column_dim") }}</v-alert
            >
          </v-col>
          <v-col cols="auto">
            <v-switch
              :label="$t('show_zero_rows')"
              v-model="showZeroRows"
              class="mt-0"
            />
          </v-col>
          <v-spacer></v-spacer>
          <v-col cols="auto" v-if="!readOnly">
            <v-btn
              @click="saveReport"
              color="primary"
              :disabled="!(formValid && headerFormValid && hasGroupBy)"
            >
              <v-icon class="mr-1" small>far fa-hdd</v-icon>
              {{
                reportPk
                  ? $t("actions.save_changes")
                  : $t("actions.save_report")
              }}
            </v-btn>
          </v-col>
        </v-row>
      </v-form>
    </div>

    <v-row>
      <v-col>
        <FlexiTableOutput v-show="displayReport" ref="outputTable" />
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import axios from "axios";
import { mapActions, mapGetters, mapState } from "vuex";
import FromToMonthEntry from "@/components/util/FromToMonthEntry";
import FromToYearEntry from "@/components/util/FromToYearEntry";
import DimensionKeySelector from "@/components/DimensionKeySelector";
import ExportMonitorWidget from "@/components/util/ExportMonitorWidget";
import FlexiTableOutput from "@/components/reporting/FlexiTableOutput";
import translators from "@/mixins/translators";
import { dimensionMixin } from "@/mixins/dimensions";
import reportTypes from "@/mixins/reportTypes";
import { FlexiReport } from "@/libs/flexi-reports";
import ReportLoadingWidget from "@/components/reporting/ReportLoadingWidget";
import isEqual from "lodash/isEqual";
import { dataTableToDjangoOrderBy } from "@/libs/sorting";
import AccessLevelSelector from "@/components/reporting/AccessLevelSelector";
import formRulesMixin from "@/mixins/formRulesMixin";
import { parseDateTime, ymDateFormat } from "@/libs/dates";
import cancellation from "@/mixins/cancellation";
import { toBase64JSON } from "@/libs/serialization";
import TagSelector from "@/components/tags/TagSelector";
import TagClassSelector from "@/components/tags/TagClassSelector";

export default {
  name: "FlexiTableEditor",

  mixins: [
    translators,
    dimensionMixin,
    reportTypes,
    formRulesMixin,
    cancellation,
  ],

  components: {
    TagClassSelector,
    TagSelector,
    AccessLevelSelector,
    ReportLoadingWidget,
    FlexiTableOutput,
    ExportMonitorWidget,
    FromToMonthEntry,
    FromToYearEntry,
    DimensionKeySelector,
  },

  props: {
    reportId: { required: false, type: Number, default: null },
  },

  data() {
    return {
      selectedItems: [],
      row: "organization",
      columns: [],
      filters: [],
      splitBy: null,
      tableDimension: null,
      selectedMetrics: [],
      selectedPlatforms: [],
      selectedReportTypes: [],
      selectedOrganizations: [],
      selectedDateRange: { start: null, end: null },
      selectedDimValues: [],
      selectedTitleTags: [],
      selectedPlatformTags: [],
      selectedOrganizationTags: [],
      selectedTagClass: null,
      tagRollUp: false,
      formValid: false,
      headerFormValid: false,
      dateModifier: "__year",
      exportHandle: null,
      exportHint: false,
      reportName: "",
      ignoreUrlFilteringParams: false,
      showErrorDialog: false,
      reportTypeSetOnLoad: false, // helps guard against updates when loading data from a stored report
      reportPk: this.reportId,
      loading: false,
      orderBy: [],
      owner: null,
      ownerOrganization: null,
      edit: !this.reportId || "edit" in this.$route.query,
      accessLevelParams: {},
      wantsSave: !!this.reportId || "wantsSave" in this.$route.query,
      showZeroRows: false,
      reportRunning: false,
      displayReport: false,
      accessibleTags: [],
      loadingTags: false,
      showRemainder: false,
      setupInProgress: false, // when true, some watchers are disabled to prevent many updates
    };
  },

  computed: {
    ...mapState({
      selectedOrganizationId: "selectedOrganizationId",
      organizations: "organizations",
      user: "user",
      lang: "appLanguage",
    }),
    ...mapGetters({
      organizationSelected: "organizationSelected",
      dateRangeStart: "dateRangeStartText",
      dateRangeEnd: "dateRangeEndText",
      enableTags: "enableTags",
    }),
    watchedRow: {
      get() {
        return this.row;
      },
      set(value) {
        // here we can react to changes in the row that were done by the user
        // not by the loading code, etc.
        // BTW, this approach seems to be an interesting way to handle
        // similar cases where the reactivity gets in the way during initialization
        this.row = value;
        this.orderBy = [];
      },
    },
    readOnly() {
      return !this.edit || !this.canEdit;
    },
    possibleRows() {
      let base = [...this.dimensions, ...this.explicitDims];
      return base;
    },
    appliedFilters() {
      let ret = {};
      if (this.selectedDateRange.start || this.selectedDateRange.end) {
        ret["date"] = this.selectedDateRange;
      }
      if (this.selectedReportTypes.length > 0) {
        ret["report_type"] = this.selectedReportTypes;
      }
      if (
        this.filters.includes("organization") &&
        this.selectedOrganizationId.length > 0
      ) {
        ret["organization"] = this.selectedOrganizations;
      }
      if (this.filters.includes("metric") && this.selectedMetrics.length > 0) {
        ret["metric"] = this.selectedMetrics;
      }
      if (
        this.filters.includes("platform") &&
        this.selectedPlatforms.length > 0
      ) {
        ret["platform"] = this.selectedPlatforms;
      }
      if (
        this.filters.includes("organization") &&
        this.selectedOrganizations.length > 0
      ) {
        ret["organization"] = this.selectedOrganizations;
      }
      // title tags
      if (
        this.filters.includes("target") &&
        this.selectedTitleTags.length > 0
      ) {
        ret["tag__target"] = this.selectedTitleTags;
      }
      // platform tags
      if (
        this.filters.includes("platform") &&
        this.selectedPlatformTags.length > 0
      ) {
        ret["tag__platform"] = this.selectedPlatformTags;
      }
      // organization tags
      if (
        this.filters.includes("organization") &&
        this.selectedOrganizationTags.length > 0
      ) {
        ret["tag__organization"] = this.selectedOrganizationTags;
      }
      // explicit dims
      this.explicitDims.forEach((dim, index) => {
        if (this.filters.includes(dim.id)) {
          let vals = this.selectedDimValues[index];
          if (vals && vals.length > 0) {
            ret[`dim${index + 1}`] = vals;
          }
        }
      });
      return ret;
    },
    appliedGroups() {
      return this.columns;
    },
    canGetData() {
      return this.row && this.hasGroupBy && this.selectedReportTypes.length > 0;
    },
    dataUrlParams() {
      return {
        primary_dimension: this.row,
        filters: toBase64JSON(this.appliedFilters),
        groups: toBase64JSON(this.appliedGroups),
        zero_rows: this.showZeroRows,
      };
    },
    selectorBaseUrl() {
      if (this.row) {
        let base = `/api/flexible-slicer/possible-values/?primary_dimension=${this.row}`;
        base += `&filters=${toBase64JSON(this.appliedFilters)}`;
        return base;
      }
      return null;
    },
    hasGroupBy() {
      return this.columns.length > 0;
    },
    reportTypeSelected() {
      return this.selectedReportTypes.length > 0;
    },
    disableDimValuesSelectors() {
      return this.selectedReportTypes.length === 0;
    },
    explicitDims() {
      if (this.selectedReportTypes.length === 1) {
        let rts = this.allReportTypes.filter(
          (item) => item.pk === this.selectedReportTypes[0]
        );
        let ret = rts[0].dimensionObjs;
        ret.forEach((item) => (item.id = item.ref));
        return ret;
      }
      return [];
    },
    selectedReportTypeObjs() {
      return this.allReportTypes.filter(
        (item) => this.selectedReportTypes.indexOf(item.pk) >= 0
      );
    },
    reportObject() {
      let rt = new FlexiReport();
      rt.name = this.reportName;
      rt.pk = this.reportPk;
      rt.reportTypes = [...this.selectedReportTypeObjs];
      rt.primaryDimension = rt.resolveDim(this.row);
      rt.filters = [];
      Object.entries(this.appliedFilters)
        .filter(([k, v]) => k !== "report_type")
        .forEach(([k, v]) => {
          if (typeof v === "object") {
            rt.filters.push({ dimension: rt.resolveDim(k), values: v });
          } else {
            rt.filters.push({ dimension: rt.resolveDim(k), values: [...v] });
          }
        });
      rt.groupBy = this.appliedGroups.map((item) => rt.resolveDim(item));
      rt.orderBy = this.orderBy;
      rt.splitBy = this.splitBy ? rt.resolveDim(this.splitBy) : this.splitBy;
      let access = this.accessLevelParams;
      rt.owner = access.owner ?? null;
      rt.ownerOrganization = access.owner_organization ?? null;
      rt.includeZeroRows = this.showZeroRows;
      rt.tagRollUp = this.tagRollUp;
      rt.tagClass = this.selectedTagClass?.pk;
      rt.showUntaggedRemainder = this.showRemainder;
      return rt;
    },
    canEdit() {
      return this.reportId
        ? this.reportObject.canEdit(this.user, this.organizations)
        : true;
    },
    accessLevel() {
      return this.owner ? "user" : this.ownerOrganization ? "org" : "sys";
    },
    tagRollUpPossible() {
      return (
        this.enableTags &&
        ["target", "platform", "organization"].includes(this.row)
      );
    },
    tagScope() {
      if (this.row === "target") {
        return "title";
      } else {
        // the name is the same as the name of the row dimension
        return this.row;
      }
    },
    anyAccessibleTag() {
      return this.accessibleTags.length > 0;
    },
    organizationCount() {
      return Object.keys(this.organizations).filter((key) => key > 0).length;
    },
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    ruleRequired(value) {
      return !!value || this.$t("required");
    },
    ruleNotEmpty(value) {
      return value.length > 0 || this.$t("not_empty");
    },
    cancelReport() {
      this.displayReport = false;
      this.$refs.outputTable.cancelReport();
    },
    async runReport() {
      this.displayReport = true;
      this.reportRunning = true;
      // used when the whole report changes. We need to reset the sorting because the old
      // might no longer be relevant
      // we want to prevent double loading of data if the change to sortBy changes URL params and
      // would lead to reload.
      this.ignoreUrlFilteringParams = true;
      try {
        await this.updateReport();
      } finally {
        this.ignoreUrlFilteringParams = false;
        this.reportRunning = false;
      }
    },
    async updateReport() {
      // used when only sorting is changed, nothing else
      await this.$refs.outputTable.updateOutput(this.reportObject);
    },
    async runExport(format) {
      if (!this.formValid) {
        console.debug("form is not valid");
        return;
      }
      if (this.canGetData) {
        try {
          this.exportHandle = await this.reportObject.startExport(format);
        } catch (error) {
          this.showSnackbar({
            content: "Could not start export: " + error,
            color: "error",
          });
        }
      }
    },
    async saveReport() {
      if (!this.wantsSave) {
        this.wantsSave = true;
        this.showSnackbar({
          content: this.$t("please_fill_in_title"),
          color: "info",
        });
        this.$nextTick(() => {
          this.$refs.titleField.focus();
        });
        return;
      }
      if (!this.formValid) {
        console.debug("form is not valid");
        return;
      }
      if (this.canGetData) {
        try {
          // update order by based on the current state of output table
          if (
            this.$refs.outputTable &&
            this.$refs.outputTable.$data.options.sortBy
          ) {
            this.orderBy = dataTableToDjangoOrderBy(
              this.$refs.outputTable.$data.options
            );
          }
          await this.reportObject.save();
          this.reportPk = this.reportObject.pk;
          // rewrite window history so that we return to this page rather than an empty one
          let location = this.$router.resolve({
            name: "flexireport",
            params: {
              reportId: this.reportPk,
            },
            query: this.readOnly ? {} : { edit: 1 },
          });
          window.history.replaceState({}, null, location.href);
          this.showSnackbar({
            content: this.$t("save_success"),
            color: "success",
          });
        } catch (error) {
          this.showSnackbar({
            content: "Could not save report: " + error,
            color: "error",
          });
        }
      }
    },
    async fetchSettings() {
      this.loading = true;
      if (this.reportPk) {
        try {
          this.setupInProgress = true;
          let resp = await axios.get(`/api/flexible-report/${this.reportPk}/`);
          this.loadSettings(resp.data);
          this.$nextTick(() => (this.setupInProgress = false));
        } catch (error) {
          this.showSnackbar({
            content: "Could not fetch stored report: " + error,
            color: "error",
          });
        } finally {
          this.loading = false;
        }
      }
      this.loading = false;
    },
    loadSettings(settings) {
      let config = settings.config;
      if (config.primary_dimension) {
        this.row = config.primary_dimension;
      }
      const configToAttr = new Map([
        ["report_type", "selectedReportTypes"],
        ["metric", "selectedMetrics"],
        ["organization", "selectedOrganizations"],
        ["platform", "selectedPlatforms"],
      ]);
      if (config.filters) {
        // deal with report_type first as it influences much more later
        let rt_filter = config.filters.find(
          (item) => item.dimension === "report_type"
        );
        if (rt_filter) {
          this.reportTypeSetOnLoad = true;
          this.selectedReportTypes = rt_filter.values;
          this.selectedDimValues = [];
          if (this.selectedReportTypes.length === 1) {
            let rt = this.allReportTypes.find(
              (item) => item.pk === this.selectedReportTypes[0]
            );
            if (rt) {
              rt.dimensions_sorted.forEach(() =>
                this.selectedDimValues.push([])
              );
            }
          }
        }
        // let's do the other filters
        for (let filter of config.filters.filter(
          (item) => item.dimension !== "report_type"
        )) {
          if (configToAttr.has(filter.dimension)) {
            this.$set(this, configToAttr.get(filter.dimension), filter.values);
            this.filters.push(filter.dimension);
          } else if (filter.dimension.substring(0, 3) === "dim") {
            this.selectedDimValues[
              Number.parseInt(filter.dimension.substring(3, 4)) - 1
            ] = filter.values;
            this.filters.push(filter.dimension);
          } else if (filter.dimension.startsWith("date")) {
            const start = parseDateTime(filter.start);
            const end = parseDateTime(filter.end);
            this.selectedDateRange = {
              start: start ? ymDateFormat(start) : null,
              end: end ? ymDateFormat(end) : null,
            };
            this.filters.push(filter.dimension);
          } else if (filter.tag_ids) {
            // deal with tag based filtering
            if (filter.dimension === "target") {
              this.selectedTitleTags = filter.tag_ids;
            } else if (filter.dimension === "platform") {
              this.selectedPlatformTags = filter.tag_ids;
            } else if (filter.dimension === "organization") {
              this.selectedOrganizationTags = filter.tag_ids;
            }
            this.filters.push(filter.dimension);
          } else {
            console.warn(`Unrecognized filter "${filter.dimension}"`);
          }
        }
      }
      if (config.group_by) {
        this.columns = config.group_by;
      }
      if (config.order_by) {
        this.orderBy = config.order_by;
      }
      if (config.split_by && config.split_by.length) {
        this.splitBy = config.split_by[0];
      } else {
        this.splitBy = null;
      }
      this.showZeroRows = config.zero_rows ?? false;
      this.tagRollUp = config.tag_roll_up ?? false;
      this.selectedTagClass = config.tag_class ?? null;
      this.showRemainder = config.show_untagged_remainder ?? false;
      this.reportName = settings.name;
      this.reportPk = settings.pk;
      this.owner = settings.owner;
      this.ownerOrganization = settings.owner_organization;
      this.accessLevelParams = {
        owner: this.owner,
        owner_organization: this.ownerOrganization,
      };
    },
    updateAccessLevel(data) {
      this.accessLevelParams = data;
    },
    async fetchAccessibleTags() {
      if (this.tagRollUpPossible) {
        this.loadingTags = true;
        this.accessibleTags = [];
        const askedScope = this.tagScope;
        let reply = await this.http({
          url: "/api/tags/tag/",
          params: { scope: this.tagScope },
        });
        if (askedScope === this.tagScope) {
          // due to async nature of the request, we need to check if the scope
          // is still the same because it could have changed in the meantime
          this.loadingTags = false;
          if (!reply.error) {
            this.accessibleTags = reply.response.data;
            if (!this.accessibleTags.length) {
              this.selectedTagClass = null;
              this.tagRollUp = false;
            }
          }
        }
      }
    },
  },

  async mounted() {
    this.loading = true;
    try {
      await this.fetchReportTypes();
      await this.fetchSettings();
      // we want to select something so that the user immediately has a report
      // he can run and see how it works. Here we select something the users
      // already know from the platforms page:
      //   * reportType = interest (most usefull, shows that interest is a separate report)
      //   * rows = platform
      //   * columns = interest type
      if (this.selectedReportTypes.length === 0) {
        const interest = this.allReportTypes.find(
          (rt) => rt.short_name === "TR"
        );
        if (interest) {
          this.selectedReportTypes.push(interest.pk);
          this.row = "platform";
          // this change has to be done after all watchers, etc. have run
          this.$nextTick(() => (this.columns = ["metric"]));
        }
      }
    } finally {
      this.loading = false;
    }
  },

  watch: {
    row() {
      this.columns = this.columns.filter((dim) => dim !== this.row);
      if (!this.setupInProgress) {
        // empty the tag class on row change to prevent unrelated class
        // from being used in filter
        this.selectedTagClass = null;
      }
      this.fetchAccessibleTags();
    },
    splitBy() {
      this.columns = this.columns.filter((dim) => dim !== this.splitBy);
      if (this.row === this.splitBy) {
        this.row = this.possibleRows.find(
          (item) => item.id !== this.splitBy
        ).id;
      }
    },
    selectedReportTypes(newValue, oldValue) {
      if (this.reportTypeSetOnLoad) {
        // first update after load should not do updates, but a new one should
        this.reportTypeSetOnLoad = false;
      } else {
        this.selectedDimValues = [];
        if (this.explicitDims) {
          // prepare the selectedDimValues array of the correct length
          this.explicitDims.forEach(() => this.selectedDimValues.push([]));
          // disable translation for dimensions that are of type integer
          this.explicitDims.forEach((dim, index) => {
            let dimName = `dim${index + 1}`;
            this.translators[dimName] = this.translators.explicitDimension;
          });
        }
        // remove groups that are for explicit dimensions
        for (let i of [1, 2, 3, 4, 5, 6, 7]) {
          this.columns = this.columns.filter((item) => item !== `dim${i}`);
        }
      }
    },
    dataUrlFilteringParams: {
      deep: true,
      handler(newVal, oldVal) {
        // we need to compare the values of newVal and oldVal as the references
        // might change without the actual value changing
        if (!isEqual(newVal, oldVal) && !this.ignoreUrlFilteringParams) {
          this.$refs.outputTable.updateOutput(this.reportObject, false);
        }
      },
    },
    filters: {
      deep: true,
      handler(newValue, oldValue) {
        for (let filter of oldValue) {
          if (!newValue.includes(filter)) {
            // this filter got disabled
            if (filter === "platform") {
              this.selectedPlatforms = [];
            } else if (filter === "organization") {
              this.selectedOrganizations = [];
            } else if (filter === "metric") {
              this.selectedMetrics = [];
            } else if (filter.startsWith("date")) {
              this.selectedDateRange = { start: null, end: null };
            } else if (filter.startsWith("dim")) {
              this.selectedDimValues[
                Number.parseInt(filter.substring(3, 4)) - 1
              ] = [];
            }
          }
        }
      },
    },
    dataUrlParams: {
      deep: true,
      handler() {
        // forget about export if the config has changed
        if (this.exportHandle) {
          this.exportHint = true;
        }
        this.exportHandle = null;
      },
    },
  },
};
</script>

<style scoped lang="scss">
.lst-item {
  color: #f5cdd5;

  &::after {
    content: ", ";
  }
  &:last-child {
    &::after {
      content: "";
    }
  }
}

.extra-info {
  font-size: 0.75rem;
  font-weight: 300;
}
</style>
