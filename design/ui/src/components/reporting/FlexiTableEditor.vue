<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<i18n lang="yaml" src="@/locales/dialog.yaml"></i18n>

<i18n lang="yaml" src="@/locales/reporting.yaml"></i18n>

<i18n lang="yaml">
en:
  run_report: Run report
  cancel_report: Cancel report
  run_export: Export
  not_empty: This field cannot be empty
  column_order_tt: This number shows the position which this dimension will occupy in the column header. It is based on the order in which the checkboxes are checked.
  download_on_separate_page: You can find all exports on the {exports_page} page.
  select_report_type: First select at least one report type.
  save_success: Report was successfully saved.
  report_title: Report title
  report_description: Report description
  please_fill_in_title: Report title is required in order to save the report.
  select_at_least_one_column_dim: At least one column dimension must be selected.
  select_at_least_one_row_dim: At least one row dimension must be selected.
  split_to_parts: Split report to parts by selected attribute
  dont_split: "-- no splitting --"
  title_tags: Tags for title filtering
  title_tags_tt: |
    Tags are used to simplify filtering of titles. You can add tags to individual titles on their corresponding pages
    or in one batch by uploading a title list.
  title_tag_class: Tag class for title filtering
  title_tag_class_tt: |
    If you want to select all tags with a specific tag class, you can do so here instead of selecting the tags one by one.
  organization_tags: Tags for organization filtering
  platform_tags: Tags for platform filtering
  tag_class_filter: Limit returned tags by tag class
  no_tag_class_filter: Allow all tag classes
  no_tags_present: There are no tags available for the selected rows.
  organization_count_tt: |
    The number of organizations you have access to. Without an organization filter, the report will be run for all
    these organizations.
  zero_rows_tooltip: Rows for which the total usage is zero will be included. Please note that this functionality is only available for some rows as CELUS very often does not know the correct list of possible values for a row (for example, it does not know all possible titles for a given platform).
  zero_rows_tooltip_trend_mode: If turned off, rows for which the usage in the base period is zero will not be be included. This allows for example filtering off of new titles for which the relative change would be infinite.
  supported_rows: Supported rows are
  when_titles: when titles are filtered by tag or "merge by tag" is active
  tags: tags
  name_the_report: Name the report
  coverage_tt: Data coverage for the selected report(s) and applied filters.
  coverage_merge_report_types_tt: Data coverage for the combination of primary and fallback reports and applied filters.
  coverage_base_tt: Data coverage in the base period.
  coverage_compared_tt: Data coverage in the compared period.
  coverage_title_tt: Data coverage shows how many months of data from a possible maximum are available for the selected report(s) and applied filters. Numbers below 100% indicate that some data is missing. Click on the number to go to a detailed breakdown.
  view_applied: View filters for '{view}' were applied to {dims}.
  metric_sum_warning_title: The configured report potentially sums several metrics together.
  metric_sum_warning_detail: This can lead to misleading results as metrics may overlap each other. To prevent this, add metric into columns or split-by, or add a metric filter with a single value.
  apply_standard_filters: Apply standard filters
  save_report_with_mailing_objects_confirm_title: Confirm saving of report with periodic export mailing
  save_report_with_mailing_objects_confirm: This report has periodic mailing of exports set up. Any changes will be reflected in the next export. Do you want to continue?
  invalid_url_parameters: Invalid URL parameters detected. Using default settings.
  trend_mode_muliindex_tt: Trend mode is not supported when multiple dimensions are used for defining rows.
  trend_mode_tt: Trend mode makes it possible to compare usage between two time periods.
  merge_report_types: Merge reports
  merge_report_types_tt: |
    When two reports are selected, merging them will preferentially use the data from the first report (highlighted) and use the second report as a fallback for missing months.
  merge_report_types_tt_primary: This report will be used as the primary source of data.
  merge_report_types_tt_secondary: This report will be used as a fallback for missing months.

cs:
  run_report: Spustit report
  cancel_report: Zrušit report
  run_export: Exportovat
  not_empty: Toto pole nesmí být prázdné
  detail: Detail
  column_order_tt: Toto číslo ukazuje pořadí v jakém bude tento rozměr uveden v hlavičce sloupců. Číslo je dané pořadím v jakém byla políčka zaškrtnuta.
  download_on_separate_page: Všechny exporty najdete na stránce {exports_page}.
  select_report_type: Nejprve vyberte alespoň jeden typ reportu.
  save_success: Report byl úspěšně uložen.
  report_title: Název reportu
  report_description: Popis reportu
  please_fill_in_title: Název reportu je vyžadován před jeho uložením
  select_at_least_one_column_dim: Musí být vybrán alespoň jeden rozměr, který definuje sloupce.
  select_at_least_one_row_dim: Musí být vybrán alespoň jeden rozměr, který definuje řádky.
  split_to_parts: Rozdělit report na části podle vybraného atributu
  dont_split: "-- nedělit --"
  title_tags: Štítky pro filtrování titulů
  title_tags_tt: |
    Pro zjednodušení filtrování titulů jsou použity štítky. Můžete je k titulům přidávat na stránce daného titulu nebo
    nahrát celý titulový seznam ze souboru.
  title_tag_class: Typ štítku pro filtrování titulů
  title_tag_class_tt: |
    Pokud chcete vybrat všechny štítky daného typu, můžete tak učinit zde místo toho, abyste vybírali jednotlivé štítky.
  platform_tags: Štítky pro filtrování platforem
  organization_tags: Štítky pro filtrování organizací
  tag_class_filter: Omezit štítky na vybraný typ
  no_tag_class_filter: Použít všchny typy štítků
  no_tags_present: Pro zvolené řádky nejsou k dispozici žádné štítky.
  organization_count_tt: |
    Počet organizací, ke kterým máte přístup. Bez filtru organizací bude report spuštěn pro všechny tyto organizace.
  zero_rows_tooltip: Budou zobrazeny i řádky, pro které je celkové využití nulové. Tato funkce je dostupná pouze pro některé řádky, protože CELUS často nezná správný seznam možných hodnot pro daný řádek (například nezná všechny možné tituly pro danou platformu).
  zero_rows_tooltip_trend_mode: Pokud je vypnuto, řádky, pro které je využití v základním období nulové, nebudou zahrnuty. To umožňuje například odfiltrování nových titulů, pro které by byla relativní změna nekonečná.
  supported_rows: Podporované řádky jsou
  when_titles: pokud jsou tituly filtrovány štítkem nebo je aktivní "sloučit podle štítku"
  tags: štítky
  name_the_report: Zvolte název reportu
  coverage_tt: Pokrytí daty pro zvolené reporty a aplikované filtry.
  coverage_merge_report_types_tt: Pokrytí daty pro kombinaci hlavního a záložního reportu a aplikovaných filtrů.
  coverage_base_tt: Pokrytí daty v základním období.
  coverage_compared_tt: Pokrytí daty v porovnávaném období.
  coverage_title_tt: Pokrytí daty ukazuje, kolik měsíců dat z možného maxima je k dispozici pro zvolené reporty a aplikované filtry. Číslo pod 100% značí, že některá data chybí. Kliknutí na číslo vás přenese na podrobný rozpis.
  view_applied: Filtry pro '{view}' byly aplikovány na {dims}.
  metric_sum_warning_title: Konfigurovaný report potenciálně sčítá několik metrik dohromady.
  metric_sum_warning_detail: To může vést k zavádějícím výsledkům, protože metriky se mohou překrývat. Řešením je přidání metriku do sloupců nebo split-by, nebo přidání filtru metrik s jedinou hodnotou.
  apply_standard_filters: Aplikovat standardní filtry
  save_report_with_mailing_objects_confirm_title: Potvrďte uložení reportu s periodickým odesíláním exportu
  save_report_with_mailing_objects_confirm: Tento report má nastaveno periodické odesílání exportu. Jakmile budou provedeny změny, budou se projevit v příštím odeslání. Opravdu chcete pokračovat?
  invalid_url_parameters: Detekovány neplatné URL parametry. Používají se výchozí hodnoty.
  trend_mode_muliindex_tt: Trend mode není podporován, pokud je vybrán více než jeden rozměr pro definici řádků.
  trend_mode_tt: Trend mode umožňuje porovnávat využití mezi dvěma časovými obdobími.
  merge_report_types: Sloučit reporty
  merge_report_types_tt: |
    Při výběru dvou reportů budou preferována data z prvního reportu (zvýrazněného) a data z druhého reportu se použijí jako záložní pro chybějící měsíce.
  merge_report_types_tt_primary: Tento report bude použit jako hlavní zdroj dat.
  merge_report_types_tt_secondary: Tento report bude použit jako záložní pro chybějící měsíce.
</i18n>

<template>
  <v-container fluid>
    <ReportLoadingWidget v-if="loading"></ReportLoadingWidget>
    <div v-else>
      <v-form>
        <v-row v-if="wantsSave">
          <v-col cols="8" md="5">
            <v-text-field
              ref="reportNameField"
              :disabled="readOnly"
              v-model="reportName"
              class="font-weight-light text-h5"
              :label="$t('report_title')"
              :rules="wantsSave ? [rules.required] : []"
            ></v-text-field>
          </v-col>
          <v-col cols="8" md="5">
            <section class="d-flex align-center description_report">
              <v-dialog
                v-model="showDescriptionDialog"
                max-width="800"
                class="edit_description_dialog"
              >
                <template v-slot:activator="{ props: activatorProps }">
                  <v-tooltip
                    location="bottom"
                    max-width="400px"
                    v-if="reportDescription"
                  >
                    <template v-slot:activator="{ props: tooltipProps }">
                      <div v-bind="tooltipProps" style="width: 100%">
                        <v-text-field
                          :disabled="readOnly"
                          v-model="reportDescription"
                          class="font-weight-light text-h5"
                          :label="$t('report_description')"
                          readonly
                          hide-details
                          v-bind="activatorProps"
                        ></v-text-field>
                      </div>
                    </template>
                    <span>
                      {{ reportDescription }}
                    </span>
                  </v-tooltip>
                  <v-text-field
                    :disabled="readOnly"
                    v-model="reportDescription"
                    class="font-weight-light text-h5"
                    :label="$t('report_description')"
                    v-else
                    readonly
                    hide-details
                    v-bind="activatorProps"
                  ></v-text-field>
                  <v-icon
                    v-if="!readOnly"
                    size="x-small"
                    v-bind="activatorProps"
                    class="ml-2 mt-3"
                  >
                    fas fa-edit
                  </v-icon>
                </template>
                <template v-slot:default="{ isActive }">
                  <v-card :title="$t('report_description')">
                    <v-card-text>
                      <v-textarea
                        v-model="newReportDescription"
                        class="font-weight-light text-h5"
                        :label="$t('report_description')"
                        :readonly="readOnly"
                        hide-details
                      ></v-textarea>
                    </v-card-text>
                    <v-card-actions>
                      <v-btn
                        variant="elevated"
                        color="defaultButton"
                        :text="$t('actions.cancel')"
                        @click="cancelDescriptionEdit"
                      ></v-btn>
                      <v-btn
                        variant="elevated"
                        color="primary"
                        :text="$t('actions.apply')"
                        @click="saveDescription"
                      ></v-btn>
                    </v-card-actions>
                  </v-card>
                </template>
              </v-dialog>
            </section>
          </v-col>
          <v-col cols="4" md="2" style="min-width: 165px">
            <AccessLevelSelector
              ref="accessLevel"
              :owner-organization="ownerOrganization"
              :disabled="readOnly"
              :model-value="accessLevel"
              @update:modelValue="updateAccessLevel"
              @update:isValidOrg="accessLevelValid = $event"
              :createNew="true"
            ></AccessLevelSelector>
          </v-col>
        </v-row>
      </v-form>
      <div
        class="d-flex"
        :class="collapsed ? 'justify-space-between' : 'justify-end'"
      >
        <v-card
          v-if="collapsed"
          class="pa-4 mt-2 mr-2 flex-grow-1"
          border
          elevation="0"
        >
          <ReportSpecOverview :report="reportObject" hide-for-view two-panes />
          <v-fab
            color="secondary"
            variant="text"
            location="bottom end"
            icon="fas fa-edit"
            absolute
            @click="collapsed = false"
            size="small"
          >
          </v-fab>
        </v-card>

        <v-btn
          @click="collapsed = !collapsed"
          color="primary"
          variant="outlined"
          icon
          size="x-small"
        >
          <v-icon size="small">
            {{ collapsed ? "fas fa-chevron-down" : "fas fa-chevron-up" }}
          </v-icon>
        </v-btn>
      </div>
      <v-form v-model="formValid">
        <v-row v-if="!collapsed">
          <v-col class="d-flex align-self-end">
            <v-autocomplete
              v-model="selectedReportTypes"
              :items="allReportTypes"
              :rules="[ruleNotEmpty]"
              :label="$t('labels.report_type')"
              item-value="pk"
              item-title="name"
              multiple
              chips
              style="min-width: 265px"
              closable-chips
              class="report_type"
              :disabled="readOnly"
            >
              <template
                #chip="{ item, index, props }"
                v-if="canMergeReportTypes && mergeReportTypes"
              >
                <v-tooltip location="bottom" max-width="600px">
                  <template #activator="{ props: tooltipProps }">
                    <v-chip
                      v-bind="{ ...props, ...tooltipProps }"
                      :color="index === 0 ? 'primary' : ''"
                      :variant="index === 0 ? 'flat' : 'tonal'"
                    ></v-chip>
                  </template>
                  {{
                    index === 0
                      ? $t("merge_report_types_tt_primary")
                      : $t("merge_report_types_tt_secondary")
                  }}
                </v-tooltip>
              </template>
            </v-autocomplete>
          </v-col>
          <v-col
            class="align-self-end"
            v-if="selectedReportTypes.length === 0 && !collapsed"
          >
            <span>
              <v-icon class="pr-2" color="orange"
                >fa fa-angle-double-left</v-icon
              >
              {{ $t("select_report_type") }}
            </span>
          </v-col>
          <v-col v-if="canMergeReportTypes" class="align-self-end" cols="auto">
            <v-tooltip location="bottom" max-width="600px">
              <template #activator="{ props }">
                <v-checkbox
                  v-model="mergeReportTypes"
                  :label="$t('merge_report_types')"
                  v-bind="props"
                  density="compact"
                ></v-checkbox>
              </template>
              {{ $t("merge_report_types_tt") }}
            </v-tooltip>
          </v-col>
          <v-col class="align-self-end">
            <v-select
              v-model="splitBy"
              :label="$t('split_to_parts')"
              :items="[{ id: null, name: $t('dont_split') }, ...possibleRows]"
              item-title="name"
              style="min-width: 265px"
              item-value="id"
              :disabled="readOnly"
            ></v-select>
          </v-col>
        </v-row>
        <v-row v-if="reportViews.length && !collapsed">
          <v-col>
            {{ $t("apply_standard_filters") }}:
            <v-tooltip
              max-width="600px"
              v-for="view in reportViews"
              :key="view.pk"
              location="bottom"
            >
              <template #activator="{ props }">
                <v-btn
                  @click="applyView(view)"
                  class="ms-2"
                  color="primary"
                  size="small"
                  :disabled="readOnly"
                  v-bind="props"
                >
                  {{ view.short_name }}
                </v-btn>
              </template>
              <div>
                <div class="font-weight-bold">{{ view.name }}</div>
                <div>{{ view.desc }}</div>
              </div>
            </v-tooltip>
          </v-col>
        </v-row>
        <v-row v-if="!collapsed">
          <v-col>
            <v-card class="pa-2">
              <v-card-title class="pt-2">{{ $t("labels.rows") }}</v-card-title>
              <v-card-text>
                <v-checkbox
                  v-for="row in possibleRows"
                  v-model="rows"
                  :label="row.name"
                  :key="row.id"
                  color="primary"
                  density="compact"
                  hide-details
                  class="mt-0"
                  :disabled="
                    row.id === splitBy ||
                    (row.id.startsWith('date') && trendMode) ||
                    !reportTypeSelected ||
                    readOnly
                  "
                  :value="row.id"
                >
                  <template #append v-if="rows.includes(row.id)">
                    <v-tooltip location="bottom" max-width="320px">
                      <template #activator="{ props }">
                        <v-chip
                          size="x-small"
                          variant="tonal"
                          color="info"
                          v-bind="props"
                          >{{ rows.indexOf(row.id) + 1 }}
                        </v-chip>
                      </template>
                      {{ $t("column_order_tt") }}
                    </v-tooltip>
                  </template>
                </v-checkbox>
              </v-card-text>
              <v-alert
                v-if="!hasValidRows && reportTypeSelected"
                type="warning"
                variant="outlined"
                class="ma-2"
              >
                {{ $t("select_at_least_one_row_dim") }}
              </v-alert>
            </v-card>
          </v-col>
          <v-col>
            <v-card class="pa-2 fill-height">
              <v-tooltip location="bottom right">
                <template #activator="{ props }">
                  <v-card-title
                    class="d-flex pt-2 justify-space-between align-start mb-1"
                    v-bind="props"
                    >{{ $t("labels.columns") }}
                    <v-switch
                      v-model="trendMode"
                      :label="$t('trend_mode.trend_mode')"
                      class="text-caption align-end ml-4 pt-0 d-flex justify-end"
                      density="compact"
                      style="min-width: 100px"
                      color="primary"
                      hide-details
                      :disabled="readOnly"
                    ></v-switch>
                  </v-card-title>
                </template>
                {{ $t("trend_mode_tt") }}
              </v-tooltip>
              <v-card-text>
                <div v-if="trendMode">
                  <div class="pt-4" style="min-width: 260px">
                    <h4>{{ $t("trend_mode.base_period") }}</h4>
                    <FromToMonthEntry
                      v-model="tmBaseDateRange"
                      :clearable="false"
                      :disabled="readOnly"
                    ></FromToMonthEntry>
                  </div>
                  <div class="pt-6">
                    <h4>{{ $t("trend_mode.compared_period") }}</h4>
                    <FromToMonthEntry
                      v-model="tmComparedDateRange"
                      :clearable="false"
                      :disabled="readOnly"
                    ></FromToMonthEntry>
                  </div>
                  <v-alert
                    v-if="baseSubsetPeriodLength !== comparedSubsetPeriodLength"
                    type="warning"
                    class="mt-4"
                    variant="outlined"
                  >
                    {{ $t("trend_mode.period_length_warning") }}
                  </v-alert>
                </div>
                <div v-else>
                  <v-checkbox
                    v-for="item in possibleRows"
                    v-model="columns"
                    :label="item.name"
                    density="compact"
                    hide-details
                    color="primary"
                    class="mt-0"
                    :disabled="
                      rows.includes(item.id) ||
                      item.id === splitBy ||
                      !reportTypeSelected ||
                      readOnly ||
                      (item.id === 'date' && columns.includes('date__year')) ||
                      (item.id === 'date__year' && columns.includes('date'))
                    "
                    :key="item.id"
                    :value="item.id"
                  >
                    <template #append v-if="columns.includes(item.id)">
                      <v-tooltip location="bottom" max-width="320px">
                        <template #activator="{ props }">
                          <v-chip
                            size="x-small"
                            variant="tonal"
                            color="info"
                            v-bind="props"
                            >{{ columns.indexOf(item.id) + 1 }}
                          </v-chip>
                        </template>
                        {{ $t("column_order_tt") }}
                      </v-tooltip>
                    </template>
                  </v-checkbox>
                </div>
              </v-card-text>
            </v-card>
          </v-col>
          <v-col>
            <v-card class="pa-2">
              <v-card-title class="pt-2 mb-1"
                >{{ $t("labels.filters") }}
              </v-card-title>
              <v-card-text>
                <div v-for="row in possibleRows" :key="row.id">
                  <v-checkbox
                    v-model="filters"
                    :label="row.name"
                    color="primary"
                    density="compact"
                    hide-details
                    class="mt-0"
                    :disabled="
                      row.id === 'report_type' ||
                      row.id === 'item' || // item filtering is not supported
                      (row.id === 'date' && filters.includes('date__year')) ||
                      (row.id === 'date__year' && filters.includes('date')) ||
                      (row.id.startsWith('date') && trendMode) ||
                      !reportTypeSelected ||
                      readOnly
                    "
                    :value="row.id"
                  >
                    <template #label>
                      {{ row.name }}
                      {{
                        row.id === "target" ||
                        row.id === "platform" ||
                        row.id === "organization"
                          ? "(" + $t("tags") + ")"
                          : null
                      }}
                      <v-tooltip
                        location="bottom"
                        v-if="
                          row.id === 'organization' && organizationCount > 1
                        "
                      >
                        <template #activator="{ props }">
                          <v-chip
                            size="x-small"
                            class="ms-2 chip_in_filter"
                            v-bind="props"
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
        <v-row v-if="tagRollUpPossible && !collapsed">
          <v-col>
            <v-card class="pa-2">
              <v-card-title class="pt-2 float-left"
                >{{ $t("labels.tags") }}
              </v-card-title>
              <v-card-text class="pt-1">
                <v-row class="align-baseline">
                  <v-col cols="auto" md="3" lg="auto" sm="5">
                    <v-checkbox
                      v-model="tagRollUp"
                      :label="$t('labels.tag_roll_up')"
                      density="compact"
                      class="mt-1"
                      color="primary"
                      :disabled="
                        !reportTypeSelected || readOnly || !anyAccessibleTag
                      "
                      :hint="!anyAccessibleTag ? $t('no_tags_present') : ''"
                      persistent-hint
                      :hide-details="anyAccessibleTag"
                    >
                    </v-checkbox>
                  </v-col>
                  <v-col md="6" lg="4" sm="12">
                    <TagClassSelector
                      v-if="tagRollUp"
                      :scope="tagScope"
                      v-model="selectedTagClass"
                      :label="$t('tag_class_filter')"
                      :placeholder="$t('no_tag_class_filter')"
                      clearable
                      style="min-width: 115px"
                      class="ps-8 pt-4 pe-8"
                      :disabled="readOnly"
                      with-visible-tags
                    ></TagClassSelector>
                  </v-col>
                  <v-col cols="auto" md="3" lg="auto">
                    <v-tooltip location="bottom" v-if="tagRollUp">
                      <template #activator="{ props }">
                        <span v-bind="props">
                          <v-checkbox
                            v-model="showRemainder"
                            :label="$t('tags_show_remainder')"
                            :disabled="readOnly"
                            density="default"
                            hide-details
                            color="primary"
                            class="mt-1"
                          ></v-checkbox>
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
        <v-row v-if="(filters.length || coverageData) && !collapsed">
          <v-col v-if="filters.length" cols="12" :md="''">
            <v-card class="fill-height">
              <v-card-title>{{ $t("labels.filter_settings") }}</v-card-title>
              <v-card-text>
                <v-container fluid>
                  <v-row align="stretch">
                    <v-col
                      cols="12"
                      md="6"
                      xl="4"
                      v-if="filters.includes('organization')"
                    >
                      <FilterCard
                        :title="$t('labels.organization')"
                        :switch-label="$t('labels.filter_by_tag')"
                        v-model="filterOrgsByTag"
                        :disabled="disableDimValuesSelectors || readOnly"
                      >
                        <DimensionKeySelector
                          :query-url="selectorBaseUrl"
                          v-model="selectedOrganizations"
                          dimension="organization"
                          :translator="translators.organization"
                          :disabled="disableDimValuesSelectors"
                          :read-only="readOnly"
                        ></DimensionKeySelector>
                        <template #alt_content>
                          <TagSelector
                            scope="organization"
                            v-model="selectedOrganizationTags"
                            :disabled="disableDimValuesSelectors || readOnly"
                            :label="$t('organization_tags')"
                            dont-check-exclusive
                          ></TagSelector>
                        </template>
                      </FilterCard>
                    </v-col>
                    <!-- platform -->
                    <v-col
                      cols="12"
                      md="6"
                      xl="4"
                      v-if="filters.includes('platform')"
                    >
                      <FilterCard
                        :title="$t('labels.platform')"
                        :switch-label="$t('labels.filter_by_tag')"
                        v-model="filterPlatformsByTag"
                        :disabled="disableDimValuesSelectors || readOnly"
                      >
                        <DimensionKeySelector
                          :query-url="selectorBaseUrl"
                          v-model="selectedPlatforms"
                          dimension="platform"
                          :translator="translators.platform"
                          :disabled="disableDimValuesSelectors"
                          :read-only="readOnly"
                        ></DimensionKeySelector>
                        <template #alt_content>
                          <TagSelector
                            scope="platform"
                            v-model="selectedPlatformTags"
                            :disabled="disableDimValuesSelectors || readOnly"
                            :label="$t('platform_tags')"
                            dont-check-exclusive
                          ></TagSelector>
                        </template>
                      </FilterCard>
                    </v-col>
                    <!-- title -->
                    <v-col
                      cols="12"
                      md="6"
                      xl="4"
                      class="d-flex"
                      v-if="filters.includes('target')"
                    >
                      <FilterCard
                        :title="$t('labels.title')"
                        :switch-label="$t('labels.filter_by_tag_class')"
                        v-model="filterTitlesByClass"
                        :disabled="disableDimValuesSelectors || readOnly"
                      >
                        <TagSelector
                          scope="title"
                          v-model="selectedTitleTags"
                          :disabled="disableDimValuesSelectors || readOnly"
                          :label="$t('title_tags')"
                          :tooltip="$t('title_tags_tt')"
                          dont-check-exclusive
                        ></TagSelector>
                        <template #alt_content>
                          <TagClassSelector
                            scope="title"
                            v-model="selectedTitleTagClass"
                            :disabled="disableDimValuesSelectors || readOnly"
                            :label="$t('title_tag_class')"
                            :tooltip="$t('title_tag_class_tt')"
                            with-visible-tags
                            clearable
                          ></TagClassSelector> </template
                      ></FilterCard>
                    </v-col>
                    <!-- metric -->
                    <v-col
                      cols="12"
                      md="6"
                      xl="4"
                      class="d-flex"
                      v-if="filters.includes('metric')"
                    >
                      <FilterCard :title="$t('labels.metric')">
                        <DimensionKeySelector
                          :query-url="selectorBaseUrl"
                          v-model="selectedMetrics"
                          dimension="metric"
                          :translator="translators.metric"
                          :disabled="disableDimValuesSelectors"
                          :read-only="readOnly"
                        ></DimensionKeySelector>
                      </FilterCard>
                    </v-col>
                    <!-- explicit dimension -->
                    <template v-for="(ed, index) in explicitDims">
                      <v-col
                        :key="index"
                        class="d-flex"
                        cols="12"
                        md="6"
                        xl="4"
                        v-if="filters.includes(ed.id)"
                      >
                        <FilterCard :title="ed.name">
                          <DimensionKeySelector
                            :query-url="selectorBaseUrl"
                            v-model="selectedDimValues[ed.id]"
                            :dimension="ed.id"
                            :translator="translators.explicitDimension"
                            :disabled="disableDimValuesSelectors"
                            :read-only="readOnly"
                          ></DimensionKeySelector>
                        </FilterCard>
                      </v-col>
                    </template>
                    <v-col
                      v-if="filters.includes('date')"
                      cols="12"
                      md="7"
                      xl="4"
                    >
                      <FilterCard :title="$t('labels.date')">
                        <FromToMonthEntry
                          v-model="selectedDateRange"
                          :disabled="readOnly"
                        ></FromToMonthEntry>
                      </FilterCard>
                    </v-col>
                    <v-col
                      v-else-if="filters.includes('date__year')"
                      cols="12"
                      md="6"
                      xl="4"
                    >
                      <FilterCard :title="$t('labels.year')">
                        <FromToYearEntry
                          v-model="selectedDateRange"
                          :disabled="readOnly"
                        ></FromToYearEntry>
                      </FilterCard>
                    </v-col>
                  </v-row>
                </v-container>
              </v-card-text>
            </v-card>
          </v-col>
          <v-col
            v-if="coverageGaugeCount"
            :cols="6 * coverageGaugeCount"
            :sm="4 * coverageGaugeCount"
            :md="3 * coverageGaugeCount"
            :xl="2 * coverageGaugeCount"
          >
            <v-card v-if="coverageData" class="fill-height">
              <v-card-title>
                <v-tooltip location="bottom" max-width="600px">
                  <template #activator="{ props }">
                    <span v-bind="props">
                      {{ $t("title_fields.data_coverage") }}
                      <v-icon color="info" class="pl-2" size="small"
                        >fa fa-info-circle</v-icon
                      >
                    </span>
                  </template>
                  <span>{{ $t("coverage_title_tt") }}</span>
                </v-tooltip>
              </v-card-title>
              <v-card-text>
                <v-row v-if="trendMode">
                  <v-col>
                    <CoverageCard
                      :label="$t('trend_mode.base_period')"
                      :tooltip="$t('coverage_base_tt')"
                      :coverage-data="coverageData.base"
                      :elevation="0"
                      :selectedDateRange="
                        trendMode ? tmBaseDateRange : selectedDateRange
                      "
                      clickable
                      @click="goToCoverageOverview"
                    ></CoverageCard>
                  </v-col>
                  <v-col>
                    <CoverageCard
                      :label="$t('trend_mode.compared_period')"
                      :tooltip="$t('coverage_compared_tt')"
                      :coverage-data="coverageData.compared"
                      :elevation="0"
                      :selectedDateRange="
                        trendMode ? tmComparedDateRange : selectedDateRange
                      "
                      clickable
                      @click="goToCoverageOverview"
                    ></CoverageCard>
                  </v-col>
                </v-row>
                <v-row v-else>
                  <v-col>
                    <CoverageCard
                      :label="$t('labels.total_coverage')"
                      :selectedDateRange="selectedDateRange"
                      :tooltip="
                        mergeReportTypes
                          ? $t('coverage_merge_report_types_tt')
                          : $t('coverage_tt')
                      "
                      :coverage-data="coverageData.overall"
                      :elevation="0"
                      clickable
                      @click="goToCoverageOverview"
                    ></CoverageCard>
                  </v-col>
                </v-row>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
        <v-row v-if="warnAgainstMetricSummation">
          <v-col>
            <v-alert type="warning" elevation="2">
              <div class="font-weight-bold">
                {{ $t("metric_sum_warning_title") }}
              </div>
              <div>{{ $t("metric_sum_warning_detail") }}</div>
            </v-alert>
          </v-col>
        </v-row>
        <v-row :class="{ 'mt-4': collapsed }">
          <v-col v-if="!reportRunning" cols="auto">
            <v-tooltip location="bottom">
              <template #activator="{ props }">
                <v-btn
                  @click="runReport"
                  :disabled="
                    !(isFormActuallyValid && hasGroupBy && hasValidRows) ||
                    reportRunning
                  "
                  v-bind="props"
                  min-width="12rem"
                  color="defaultButton"
                >
                  <v-icon size="small" color="green lighten-2" class="mr-2"
                    >fa fa-play
                  </v-icon>
                  {{ $t("run_report") }}
                </v-btn>
              </template>
              {{ $t("run_report_tt") }}
            </v-tooltip>
          </v-col>
          <v-col v-if="reportRunning" cols="auto">
            <v-tooltip location="bottom">
              <template #activator="{ props }">
                <v-btn
                  @click="cancelReport"
                  :disabled="!(hasGroupBy && reportRunning)"
                  v-bind="props"
                  min-width="12rem"
                >
                  <v-progress-circular
                    indeterminate
                    color="red lighten-2"
                    size="18"
                    width="2"
                    class="mr-2"
                  ></v-progress-circular>
                  {{ $t("cancel_report") }}
                </v-btn>
              </template>
              {{ $t("cancel_report_tt") }}
            </v-tooltip>
          </v-col>
          <v-col cols="auto">
            <v-menu offset-y class="mb-3">
              <template v-slot:activator="{ props }">
                <v-btn
                  v-bind="props"
                  :disabled="
                    !(isFormActuallyValid && hasGroupBy && hasValidRows)
                  "
                  color="defaultButton"
                >
                  <v-icon size="small" color="blue lighten-2" class="mr-2"
                    >fas fa-file-export
                  </v-icon>
                  {{ $t("run_export") }}
                </v-btn>
              </template>
              <v-list>
                <v-list-item @click="runExport('XLSX')">
                  <v-list-item-title
                    >{{ $t("format.excel") }}
                  </v-list-item-title>
                </v-list-item>
                <v-list-item @click="runExport('XLSX_NO_CHARTS')">
                  <v-list-item-title
                    >{{ $t("format.excel_no_charts") }}
                  </v-list-item-title>
                </v-list-item>
                <v-list-item @click="runExport('ZIP_CSV')">
                  <v-list-item-title>{{ $t("format.csv") }}</v-list-item-title>
                </v-list-item>
              </v-list>
            </v-menu>
          </v-col>
          <v-col cols="auto">
            <ExportMonitorWidget
              v-if="exportHandle"
              :export-id="exportHandle.pk"
            ></ExportMonitorWidget>
            <v-alert
              v-else-if="exportHint"
              type="info"
              variant="outlined"
              dismissible
            >
              <i18n-t keypath="download_on_separate_page">
                <template #exports_page>
                  <router-link :to="{ name: 'exports' }"
                    >{{ $t("pages.exports") }}
                  </router-link>
                </template>
              </i18n-t>
            </v-alert>
          </v-col>
          <v-col cols="auto">
            <v-alert
              type="warning"
              v-if="
                (!hasGroupBy || !hasValidRows) && selectedReportTypes.length
              "
              variant="outlined"
            >
              <span v-if="!hasValidRows">{{
                $t("select_at_least_one_row_dim")
              }}</span>
              <span v-else>{{ $t("select_at_least_one_column_dim") }}</span>
            </v-alert>
          </v-col>
          <v-col cols="auto" class="pt-0">
            <v-tooltip location="top" max-width="600px">
              <template #activator="{ props }">
                <span v-bind="props">
                  <v-switch
                    :label="
                      trendMode
                        ? $t('show_zero_rows_trend_mode')
                        : $t('show_zero_rows')
                    "
                    color="primary"
                    v-model="showZeroRows"
                    class="mt-0"
                    :disabled="cannotShowZeroRows"
                    v-if="!collapsed"
                  ></v-switch>
                </span>
              </template>
              <span>
                {{ zeroRowsTooltip }}
                <div v-if="!trendMode"></div>
                <ul v-if="!trendMode">
                  <li>{{ $t("labels.platform") }}</li>
                  <li>{{ $t("labels.organization") }}</li>
                  <li>{{ $t("labels.title") }} ({{ $t("when_titles") }})</li>
                </ul>
              </span>
            </v-tooltip>
          </v-col>
          <v-col cols="auto" class="pt-0" v-if="!trendMode && !collapsed">
            <!-- row totals do not make sense in trend mode -->
            <v-switch
              color="primary"
              v-model="showTotals"
              :label="$t('show_totals')"
              class="mt-0"
            ></v-switch>
          </v-col>
          <v-spacer></v-spacer>
          <v-col cols="auto" v-if="!readOnly">
            <v-btn
              @click="wantsSave ? saveReport() : (showNameEditDialog = true)"
              color="primary"
              :disabled="
                !(isFormActuallyValid && hasGroupBy) || !accessLevelValid
              "
            >
              <v-icon class="mr-2" size="small">far fa-hdd</v-icon>
              {{
                reportPk
                  ? $t("actions.save_changes")
                  : $t("actions.save_report")
              }}
            </v-btn>
          </v-col>
        </v-row>
      </v-form>
      <v-dialog v-model="showNameEditDialog" max-width="640px">
        <ReportNamingWidget
          :title="$t('name_the_report')"
          :input-label="$t('labels.report_name')"
          :createNew="true"
          @cancel="showNameEditDialog = false"
          @update="firstSave"
        ></ReportNamingWidget>
      </v-dialog>
    </div>
    <v-row>
      <v-col>
        <FlexiTableOutput
          v-show="displayReport"
          :show-row-totals="showTotals"
          ref="outputTable"
          @update:ordering="handleOrderingChange"
        ></FlexiTableOutput>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import CoverageCard from "@/components/coverage/CoverageCard.vue";
import AccessLevelSelector from "@/components/reporting/AccessLevelSelector";
import FilterCard from "@/components/reporting/FilterCard.vue";
import FlexiTableOutput from "@/components/reporting/FlexiTableOutput";
import ReportLoadingWidget from "@/components/reporting/ReportLoadingWidget";
import ReportNamingWidget from "@/components/reporting/ReportNamingWidget.vue";
import ReportSpecOverview from "@/components/reporting/ReportSpecOverview.vue";
import DimensionKeySelector from "@/components/selectors/DimensionKeySelector";
import TagClassSelector from "@/components/tags/TagClassSelector";
import TagSelector from "@/components/tags/TagSelector";
import ExportMonitorWidget from "@/components/util/ExportMonitorWidget";
import FromToMonthEntry from "@/components/util/FromToMonthEntry";
import FromToYearEntry from "@/components/util/FromToYearEntry";
import {
  anyDateToYm,
  lastCoveredYearDate,
  parseDateTime,
  ymDateFormat,
  ymDateParse,
} from "@/libs/dates";
import { explicitDimensions } from "@/libs/dimensions";
import { FlexiReport } from "@/libs/flexi-reports";
import { fromBase64Object, toBase64JSON } from "@/libs/serialization";
import cancellation from "@/mixins/cancellation";
import { dimensionMixin } from "@/mixins/dimensions";
import formRulesMixin from "@/mixins/formRulesMixin";
import reportTypes from "@/mixins/reportTypes";
import stateTracking from "@/mixins/stateTracking";
import translators from "@/mixins/translators";
import axios from "axios";
import addYears from "date-fns/addYears";
import differenceInCalendarMonths from "date-fns/differenceInCalendarMonths";
import lastDayOfYear from "date-fns/lastDayOfYear";
import startOfYear from "date-fns/startOfYear";
import isEqual from "lodash/isEqual";
import { useGoTo } from "vuetify";
import { mapActions, mapGetters, mapState } from "vuex";

export default {
  name: "FlexiTableEditor",

  mixins: [
    translators,
    dimensionMixin,
    reportTypes,
    formRulesMixin,
    cancellation,
    stateTracking,
  ],

  components: {
    FilterCard,
    ReportNamingWidget,
    CoverageCard,
    TagClassSelector,
    TagSelector,
    AccessLevelSelector,
    ReportLoadingWidget,
    FlexiTableOutput,
    ExportMonitorWidget,
    FromToMonthEntry,
    FromToYearEntry,
    DimensionKeySelector,
    ReportSpecOverview,
  },

  props: {
    reportId: { required: false, type: Number, default: null },
  },

  setup() {
    const goTo = useGoTo();
    return { goTo };
  },

  data() {
    const lastCoveredDate = lastCoveredYearDate();
    const comparedStart = startOfYear(lastCoveredDate);
    const comparedEnd = lastDayOfYear(lastCoveredDate);
    const baseStart = addYears(comparedStart, -1);
    const baseEnd = addYears(comparedEnd, -1);
    return {
      watchedAttrs: [
        { name: "selectedReportTypes", type: Array, var: "rt" },
        { name: "rows", type: Array, var: "r" },
        { name: "columns", type: Array, var: "c" },
        { name: "filters", type: Array, var: "f" },
        { name: "splitBy", type: String, var: "sb" },
        { name: "orderBy", type: Array, var: "o" },

        { name: "selectedMetrics", type: Array, var: "m", alwaysTrack: true },
        { name: "selectedPlatforms", type: Array, var: "p" },
        { name: "selectedOrganizations", type: Array, var: "org" },
        { name: "selectedDateRange", type: Object, var: "dr" },
        { name: "selectedDimValues", type: Object, var: "dv" },

        { name: "selectedTitleTags", type: Array, var: "tt" },
        { name: "selectedTitleTagClass", type: Object, var: "ttc" },
        { name: "selectedPlatformTags", type: Array, var: "pt" },
        { name: "selectedOrganizationTags", type: Array, var: "ot" },
        { name: "selectedTagClass", type: Object, var: "tc" },

        { name: "filterOrgsByTag", type: Boolean, var: "fot" },
        { name: "filterPlatformsByTag", type: Boolean, var: "fpt" },
        { name: "filterTitlesByClass", type: Boolean, var: "ftc" },

        { name: "showZeroRows", type: Boolean, var: "zr" },
        { name: "showTotals", type: Boolean, var: "st" },
        { name: "tagRollUp", type: Boolean, var: "tru" },
        { name: "showRemainder", type: Boolean, var: "sr" },

        { name: "trendMode", type: Boolean, var: "tm" },
        { name: "tmBaseDateRange", type: Object, var: "tmb" },
        { name: "tmComparedDateRange", type: Object, var: "tmc" },
        { name: "autoRun", type: Boolean, var: "run" },
        { name: "collapsed", type: Boolean, var: "col" },
      ],
      selectedItems: [],
      rows: ["organization"],
      columns: [],
      collapsed: false,
      filters: [],
      rules: {
        required: (value) => !!value || this.$t("please_fill_in_title"),
      },
      splitBy: null,
      tableDimension: null,
      selectedMetrics: [],
      selectedPlatforms: [],
      selectedReportTypes: [],
      selectedOrganizations: [],
      selectedDateRange: { start: null, end: null },
      selectedDimValues: {},
      selectedTitleTags: [],
      selectedTitleTagClass: null,
      selectedPlatformTags: [],
      selectedOrganizationTags: [],
      selectedTagClass: null, // this one is for the tag roll-up, not the title tag class
      filterOrgsByTag: false,
      filterPlatformsByTag: false,
      filterTitlesByClass: false,
      trendMode: false,
      mergeReportTypes: true,
      tmBaseDateRange: {
        start: ymDateFormat(baseStart),
        end: ymDateFormat(baseEnd),
      },
      tmComparedDateRange: {
        start: ymDateFormat(comparedStart),
        end: ymDateFormat(comparedEnd),
      },
      tagRollUp: false,
      formValid: false,
      dateModifier: "__year",
      exportHandle: null,
      exportHint: false,
      reportName: "",
      reportDescription: "",
      ignoreUrlFilteringParams: false,
      reportTypeSetOnLoad: false, // helps guard against updates when loading data from a stored report
      reportPk: this.reportId,
      loading: false,
      orderBy: [],
      owner: null,
      ownerOrganization: null,
      wantsSave: !!this.reportId || "wantsSave" in this.$route.query,
      showZeroRows: false,
      showTotals: true,
      reportRunning: false,
      displayReport: false,
      accessibleTags: [],
      loadingTags: false,
      showRemainder: false,
      setupInProgress: false, // when true, some watchers are disabled to prevent many updates
      showNameEditDialog: false,
      coverageData: null,
      initialLoad: true,
      reportViews: [], // list of standard views associated with selected rt
      mailingCount: 0,
      accessLevelValid: true,
      showDescriptionDialog: false,
      newReportDescription: "",
      autoRun: false,
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
      globallySelectedOrganization: "selectedOrganization",
      dateRangeStart: "dateRangeStartText",
      dateRangeCoverageEnd: "dateRangeCoverageEndText",
      reportsWithoutCoverage: "reportTypesWithoutCoverage",
    }),
    trackedState: {
      get() {
        if (this.reportId || this.setupInProgress) {
          return {};
        }

        let out = {};
        this.watchedAttrs.forEach((attr) => {
          let shouldInclude = false;

          if (attr.name === "selectedDimValues") {
            shouldInclude =
              this[attr.name] &&
              Object.values(this[attr.name]).some(
                (arr) => Array.isArray(arr) && arr.length > 0,
              );
          } else if (attr.type === Boolean) {
            shouldInclude = this[attr.name] === true;
          } else if (this[attr.name] && this[attr.name].length !== 0) {
            shouldInclude = true;
          }
          if (shouldInclude) {
            out[attr.var || attr.name] = this[attr.name];
          }
        });
        return out;
      },
      set(val) {
        if (this.reportId || this.setupInProgress) {
          return;
        }
        // use the _restoreAttr method from the mixin
        this.watchedAttrs.forEach((attr) => {
          this._restoreAttr(attr, val);
        });
      },
    },
    readOnly() {
      return !this.canEdit;
    },
    possibleRows() {
      let base = [...this.dimensions, ...this.explicitDims];
      if (this.trendMode) {
        base = base.filter((d) => !d.id.startsWith("date"));
      }
      if (this.selectedReportTypes.length <= 1) {
        // only show report type if there is more than one selected
        base = base.filter((d) => d.id !== "report_type");
      }
      // remove items if not all report types use items
      if (!this.showItems) {
        base = base.filter((d) => d.id !== "item");
      }
      // remove titles if not all report types use titles
      if (!this.showTitles) {
        base = base.filter((d) => d.id !== "target");
      }
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
        !this.filterPlatformsByTag &&
        this.selectedPlatforms.length > 0
      ) {
        ret["platform"] = this.selectedPlatforms;
      }
      if (
        this.filters.includes("organization") &&
        !this.filterOrgsByTag &&
        this.selectedOrganizations.length > 0
      ) {
        ret["organization"] = this.selectedOrganizations;
      }
      // title tags
      if (
        this.filters.includes("target") &&
        !this.filterTitlesByClass &&
        this.selectedTitleTags.length > 0
      ) {
        ret["tag__target"] = this.selectedTitleTags;
      }
      // title tag class
      // we only allow single selection, but it behaves like a list
      // in the API
      if (
        this.filters.includes("target") &&
        this.filterTitlesByClass &&
        this.selectedTitleTagClass
      ) {
        ret["tag_class__target"] = [this.selectedTitleTagClass.pk];
      }
      // platform tags
      if (
        this.filters.includes("platform") &&
        this.filterPlatformsByTag &&
        this.selectedPlatformTags.length > 0
      ) {
        ret["tag__platform"] = this.selectedPlatformTags;
      }
      // organization tags
      if (
        this.filters.includes("organization") &&
        this.filterOrgsByTag &&
        this.selectedOrganizationTags.length > 0
      ) {
        ret["tag__organization"] = this.selectedOrganizationTags;
      }
      // explicit dims
      this.explicitDims.forEach((dim, index) => {
        if (this.filters.includes(dim.id)) {
          let vals = this.selectedDimValues[dim.id];
          if (vals && vals.length > 0) {
            ret[dim.id] = vals;
          }
        }
      });
      return ret;
    },
    appliedGroups() {
      return this.columns;
    },
    canGetData() {
      return (
        this.hasValidRows &&
        this.hasGroupBy &&
        this.selectedReportTypes.length > 0
      );
    },
    hasValidRows() {
      return this.rows.length > 0;
    },
    coverageDefiningUrlParams() {
      // subset of url params which have to be watched to trigger a coverage reload
      return {
        filters: toBase64JSON(this.appliedFilters),
        base_period_filters: toBase64JSON(this.tmBaseDateRange),
        compared_period_filters: toBase64JSON(this.tmComparedDateRange),
        merge_report_types: this.canMergeReportTypes && this.mergeReportTypes,
        has_report_types: this.allReportTypes.length > 0, // ensure change when rts are loaded
        trend_mode: this.trendMode, // ensure change when trend mode changes
      };
    },
    selectorBaseUrl() {
      // this url is used to get the possible values for the selector
      // it does not matter which dimension is used, only the filters are important
      // so we use a static primary dimension to prevent unnecessary reloading
      // of the data when primary dimensions change
      let base = `/api/flexible-slicer/possible-values/?primary_dimensions=${toBase64JSON(
        ["organization"],
      )}`;
      base += `&filters=${toBase64JSON(this.appliedFilters)}`;
      return base;
    },
    hasGroupBy() {
      return this.columns.length > 0 || this.trendMode;
    },
    reportTypeSelected() {
      return this.selectedReportTypes.length > 0;
    },
    showItems() {
      // for some reason, the `rt` could be undefined here, so there is an extra check
      return this.selectedReportTypeObjs.every((rt) => rt?.uses_items);
    },
    showTitles() {
      // for some reason, the `rt` could be undefined here, so there is an extra check
      return this.selectedReportTypeObjs.every((rt) => rt?.uses_titles);
    },
    disableDimValuesSelectors() {
      return this.selectedReportTypes.length === 0;
    },
    explicitDims() {
      if (this.selectedReportTypes.length === 1) {
        let rts = this.allReportTypes.filter(
          (item) => item.pk === this.selectedReportTypes[0],
        );
        if (rts.length === 0) {
          return [];
        }
        let ret = rts[0].dimensionObjs;
        ret.forEach((item) => (item.id = item.ref));
        return ret;
      } else if (this.selectedReportTypes.length > 1) {
        // only show dimensions which are shared by all selected report types
        // and have the same position (and are represented by the same db column)
        let out = [];
        const rt1 = this.allReportTypes.find(
          (item) => item.pk === this.selectedReportTypes[0],
        );
        if (!rt1) {
          return [];
        }
        let others = this.allReportTypes.filter(
          (item) => this.selectedReportTypes.indexOf(item.pk) > 0,
        );
        rt1.dimensionObjs.forEach((dim, idx) => {
          if (others.every((rt) => rt.dimensionObjs[idx]?.pk === dim.pk)) {
            dim.id = dim.ref;
            out.push(dim);
          }
        });
        return out;
      }
      return [];
    },
    selectedReportTypeObjs() {
      return this.selectedReportTypes
        .map((pk) => this.allReportTypes.find((item) => item.pk === pk))
        .filter((rt) => !!rt);
    },
    reportObject() {
      let rt = new FlexiReport();
      rt.name = this.reportName;
      rt.description = this.reportDescription;
      rt.pk = this.reportPk;
      rt.reportTypes = [...this.selectedReportTypeObjs];
      rt.primaryDimensions = this.rows.map((row) => rt.resolveDim(row));
      rt.filters = [];
      Object.entries(this.appliedFilters)
        .filter(([k, v]) => k !== "report_type")
        .forEach(([k, v]) => {
          if (typeof v === "object" && !Array.isArray(v)) {
            if (v.start !== undefined || v.end !== undefined) {
              rt.filters.push({
                dimension: rt.resolveDim(k),
                start: v.start,
                end: v.end,
              });
            } else {
              rt.filters.push({ dimension: rt.resolveDim(k), values: v });
            }
          } else {
            rt.filters.push({ dimension: rt.resolveDim(k), values: [...v] });
          }
        });
      rt.groupBy = this.appliedGroups.map((item) => rt.resolveDim(item));
      rt.orderBy = this.orderBy;
      rt.splitBy = this.splitBy ? rt.resolveDim(this.splitBy) : this.splitBy;
      rt.owner = this.owner;
      rt.ownerOrganization = this.ownerOrganization;
      rt.includeZeroRows = this.showZeroRows;
      rt.includeTotals = this.showTotals;
      rt.tagRollUp = this.tagRollUp;
      rt.tagClass = this.selectedTagClass?.pk;
      rt.showUntaggedRemainder = this.showRemainder;
      rt.trendMode = this.trendMode;
      rt.mergeReportTypes = this.canMergeReportTypes && this.mergeReportTypes;
      rt.baseSubsetDateRange = this.tmBaseDateRange;
      rt.comparedSubsetDateRange = this.tmComparedDateRange;
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
      if (this.usesMultiIndex) return false; // multiindex does not support tag roll-up
      return this.rows.some((row) =>
        ["target", "platform", "organization"].includes(row),
      );
    },
    tagScope() {
      // used for tag roll-up - not used for multiindex
      if (this.rows.includes("target")) {
        return "title";
      } else if (this.rows.length === 1) {
        // the name is the same as the name of the row dimension
        return this.rows[0];
      }
      return null;
    },
    anyAccessibleTag() {
      return this.accessibleTags.length > 0;
    },
    organizationCount() {
      return Object.keys(this.organizations).filter((key) => key > 0).length;
    },
    cannotShowZeroRows() {
      // we cannot show zero rows if we use multiindex - the backend does not support this
      if (this.usesMultiIndex) return true;
      // if we sum by tag, we need to allow zero rows
      if (this.tagRollUp) return false;
      // in trend mode, we can show zero rows, because the meaning is different
      if (this.trendMode) return false;
      // if rows are organization or platform, we can show zero rows
      if (this.rows.some((row) => ["organization", "platform"].includes(row)))
        return false;
      // for titles, we can only show zero rows if we have the titles
      // limited by a tag
      if (this.rows.includes("target") && this.selectedTitleTags.length > 0)
        return false;
      // otherwise, we cannot show zero rows
      return true;
    },
    zeroRowsTooltip() {
      if (this.trendMode) {
        return this.$t("zero_rows_tooltip_trend_mode");
      }
      return this.$t("zero_rows_tooltip", {
        row: this.rows.map((row) => this.$t(row)).join(", "),
      });
    },
    baseSubsetPeriodLength() {
      if (this.trendMode) {
        return this.dateRangeLength(this.tmBaseDateRange);
      }
      return 0;
    },
    comparedSubsetPeriodLength() {
      if (this.trendMode) {
        return this.dateRangeLength(this.tmComparedDateRange);
      }
      return 0;
    },
    coverageGaugeCount() {
      // if any of the selected report types do not support coverage,
      // we do not show it
      for (let rt of this.selectedReportTypeObjs) {
        if (this.reportsWithoutCoverage.includes(rt.short_name)) return 0;
      }
      return this.trendMode ? 2 : 1;
    },
    warnAgainstMetricSummation() {
      // if metric is not in splitBy, in columns, or has a filter to one value
      // we want to warn the user that he may be summing up apples and oranges
      if (this.splitBy === "metric") return false;
      if (this.columns.includes("metric") && !this.trendMode) return false;
      if (this.rows.includes("metric")) return false;
      if (this.filters.includes("metric") && this.selectedMetrics.length === 1)
        return false;
      return true;
    },
    reportDescriptionClass() {
      return this.readOnly ? "text-grey-lighten-1" : "";
    },
    shouldAutoRun() {
      return (
        this.autoRun &&
        !this.initialLoad &&
        !this.setupInProgress &&
        this.canGetData &&
        this.hasGroupBy &&
        this.selectedReportTypes.length > 0 &&
        this.isFormActuallyValid !== false &&
        !this.reportRunning &&
        !this.displayReport
      );
    },
    isFormActuallyValid() {
      if (this.collapsed) {
        const hasReportTypes = this.selectedReportTypes.length > 0;
        const hasValidGroupBy = this.hasGroupBy;
        const hasValidName =
          !this.wantsSave || (this.reportName && this.reportName.length > 0);
        return hasReportTypes && hasValidGroupBy && hasValidName;
      }
      return this.formValid;
    },
    usesMultiIndex() {
      return this.rows.length > 1;
    },
    canMergeReportTypes() {
      // TODO: we need more sophisticated check here
      // probably based on report type superseding configuration
      // or simply predefined in a constant here
      // We probably want this only for TR and TR51, DR and DR51, and PR and PR51
      return this.selectedReportTypes.length === 2;
    },
  },

  methods: {
    // goTo() {
    //   return goTo;
    // },
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    deserialize(attr, value) {
      switch (attr.type) {
        case Object:
          return value;
        case Array:
          return value;
        case String:
          return String(value);
        case Number:
          return parseInt(value);
        case Boolean:
          if (typeof value === "boolean") {
            return value;
          } else {
            return value === "true";
          }
        default:
          return value;
      }
    },
    isValidDim(value) {
      return (
        !value.startsWith("dim") ||
        this.explicitDims.find((dim) => dim.id === value)
      );
    },
    ruleNotEmpty(modelValue) {
      return modelValue.length > 0 || this.$t("not_empty");
    },
    cancelReport() {
      this.displayReport = false;
      this.$refs.outputTable.cancelReport();
    },
    dateRangeLength(range) {
      if (range.start && range.end) {
        const end = ymDateParse(range.end);
        const start = ymDateParse(range.start);
        return differenceInCalendarMonths(end, start);
      }
      return 0;
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
      await this.$refs.outputTable.updateOutput(this.reportObject);
    },
    async runExport(format) {
      if (!this.isFormActuallyValid) {
        return;
      }
      if (this.canGetData) {
        try {
          this.updateOrderByFromOutputTable();
          this.exportHandle = await this.reportObject.startExport(format);
        } catch (error) {
          this.showSnackbar({
            content: "Could not start export: " + error,
            color: "error",
          });
        }
      }
    },
    updateOrderByFromOutputTable() {
      // update order by based on the current state of output table
      if (this.$refs.outputTable && this.$refs.outputTable.ordering) {
        this.orderBy = [this.$refs.outputTable.ordering];
      }
    },
    handleOrderingChange(ordering) {
      if (ordering) {
        this.orderBy = [ordering];
      }
    },
    async firstSave({ title, description, access }) {
      this.reportName = title;
      this.reportDescription = description;
      this.owner = access.owner;
      this.ownerOrganization = access.owner_organization;
      if (!this.wantsSave) {
        this.wantsSave = true;
      }
      this.showNameEditDialog = false;
      await this.saveReport();
    },
    async saveReport() {
      if (this.wantsSave && !this.reportName) {
        if (this.$refs.reportNameField) {
          this.$refs.reportNameField.validate();
          await this.goTo(this.$refs.reportNameField.$el, {
            duration: 300,
            offset: -100,
          });
          await this.$nextTick();
          this.$refs.reportNameField.focus();
          const inputElement =
            this.$refs.reportNameField.$el.querySelector("input");
          if (inputElement) {
            inputElement.focus();
          }
        }
        return;
      }
      if (!this.isFormActuallyValid) {
        return;
      }
      // if the report has some mailing objects, ask user to confirm saving
      if (this.mailingCount > 0) {
        const confirm = await this.$confirm(
          this.$t("save_report_with_mailing_objects_confirm"),
          {
            title: this.$t("save_report_with_mailing_objects_confirm_title"),
            buttonTrueText: this.$t("save"),
            buttonFalseText: this.$t("cancel"),
            icon: "far fa-hdd",
            width: 600,
            color: "primary",
          },
        );
        if (!confirm) {
          return;
        }
      }
      if (this.canGetData) {
        try {
          // update order by based on the current state of output table
          this.updateOrderByFromOutputTable();
          await this.reportObject.save();
          const savedReportPk = this.reportObject.pk;
          this.reportPk = savedReportPk;
          this.setupInProgress = true;
          // rewrite window history so that we return to this page rather than an empty one
          let location = this.$router.resolve({
            name: "flexireport",
            params: {
              reportId: savedReportPk,
            },
            query: this.$route.query,
          });
          window.history.replaceState({}, null, location.href);
          this.$nextTick(() => {
            this.setupInProgress = false;
          });

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
          this.mailingCount = resp.data.mailing_count;
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
      // Handle both old primary_dimension and new primary_dimensions for backward compatibility
      if (config.primary_dimensions) {
        this.rows = config.primary_dimensions;
      } else if (config.primary_dimension) {
        this.rows = [config.primary_dimension];
      }
      if (config.filters) {
        // deal with report_type first as it influences much more later
        let rt_filter = config.filters.find(
          (item) => item.dimension === "report_type",
        );
        if (rt_filter) {
          this.reportTypeSetOnLoad = true;
          this.selectedReportTypes = rt_filter.values;
          this.selectedDimValues = {};
          if (this.selectedReportTypes.length === 1) {
            let rt = this.allReportTypes.find(
              (item) => item.pk === this.selectedReportTypes[0],
            );
            if (rt) {
              rt.dimensions_sorted.forEach(
                (dim) => (this.selectedDimValues[dim.id] = []),
              );
            }
          }
        }

        // let's do the other filters
        const configToAttr = new Map([
          ["metric", "selectedMetrics"],
          ["organization", "selectedOrganizations"],
          ["platform", "selectedPlatforms"],
        ]);
        for (let filter of config.filters.filter(
          (item) => item.dimension !== "report_type",
        )) {
          if (filter.tag_ids) {
            // deal with tag based filtering
            // tags can be used on dimensions both in `configToAttr` and
            // outside of it (titles) so we check it first
            if (filter.dimension === "target") {
              this.selectedTitleTags = filter.tag_ids;
            } else if (filter.dimension === "platform") {
              this.selectedPlatformTags = filter.tag_ids;
              this.filterPlatformsByTag = true;
            } else if (filter.dimension === "organization") {
              this.selectedOrganizationTags = filter.tag_ids;
              this.filterOrgsByTag = true;
            }
            this.filters.push(filter.dimension);
          } else if (filter.tag_class_ids) {
            if (filter.dimension === "target") {
              if (filter.tag_class_ids.length > 0) {
                this.selectedTitleTagClass = filter.tag_class_ids[0];
                this.filterTitlesByClass = true;
                this.filters.push(filter.dimension);
              }
            } else {
              console.warn("unsupported tag class filter: ", filter);
            }
          } else if (configToAttr.has(filter.dimension)) {
            this[configToAttr.get(filter.dimension)] = filter.values;
            this.filters.push(filter.dimension);
          } else if (filter.dimension.substring(0, 3) === "dim") {
            this.selectedDimValues[filter.dimension] = filter.values;
            this.filters.push(filter.dimension);
          } else if (filter.dimension.startsWith("date")) {
            const start = parseDateTime(filter.start);
            const end = parseDateTime(filter.end);
            this.selectedDateRange = {
              start: start ? ymDateFormat(start) : null,
              end: end ? ymDateFormat(end) : null,
            };
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
      this.showTotals = config.row_totals ?? true;
      this.tagRollUp = config.tag_roll_up ?? false;
      this.selectedTagClass = config.tag_class ?? null;
      this.showRemainder = config.show_untagged_remainder ?? false;
      this.reportName = settings.name;
      this.reportDescription = settings.description;
      this.reportPk = settings.pk;
      this.owner = settings.owner;
      this.ownerOrganization = settings.owner_organization;
      // trend mode
      this.trendMode = config.trend_mode ?? false;
      if (config.base_subset_filters) {
        const fltr = config.base_subset_filters.find(
          (fltr) => fltr.start && fltr.end,
        );
        if (fltr) {
          this.tmBaseDateRange = {
            start: anyDateToYm(fltr.start),
            end: anyDateToYm(fltr.end),
          };
        }
      }
      if (config.compared_subset_filters) {
        const fltr = config.compared_subset_filters.find(
          (fltr) => fltr.start && fltr.end,
        );
        if (fltr) {
          this.tmComparedDateRange = {
            start: anyDateToYm(fltr.start),
            end: anyDateToYm(fltr.end),
          };
        }
      }
    },
    updateAccessLevel({ owner, owner_organization }) {
      this.owner = owner;
      this.ownerOrganization = owner_organization;
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
    async fetchCoverageData() {
      if (
        this.selectedReportTypes.length &&
        this.selectedReportTypeObjs.length &&
        this.coverageGaugeCount > 0
      ) {
        this.coverageData = await this.reportObject.getCoverage();
      }
    },
    goToCoverageOverview() {
      const routerCoverageOverview = this.$router.resolve({
        name: "data-coverage-overview",
        query: {
          rtid:
            this.selectedReportTypes.length === 1
              ? this.selectedReportTypes[0]
              : undefined,
        },
      });
      window.open(routerCoverageOverview.href, "_blank");
    },
    async fetchReportViews() {
      if (this.selectedReportTypes.length === 1) {
        let reply = await this.http({
          url: `/api/report-type/${this.selectedReportTypes[0]}/report-views/`,
          params: { full: true },
        });
        if (!reply.error) {
          this.reportViews = reply.response.data.filter(
            (item) => item.is_standard_view,
          );
        }
      }
    },
    applyView(view) {
      let filteredDims = []; // collect info about applied filters for display
      // apply metric filter
      if (
        view.metric_allowed_value_ids &&
        view.metric_allowed_value_ids.length
      ) {
        if (!this.filters.includes("metric")) {
          this.filters.push("metric");
        }
        this.selectedMetrics = view.metric_allowed_value_ids;
        filteredDims.push("Metric");
      }
      // empty all explicit dimension filters
      explicitDimensions.forEach((dim, index) => {
        this.selectedDimValues[dim.id] = [];
        if (this.filters.includes(dim)) {
          this.filters = this.filters.filter((item) => item !== dim);
        }
      });
      // apply filters to explicit dimensions
      for (let df of view.dimension_filters) {
        let expDim = this.explicitDims.find(
          (dim) => dim.shortName === df.dimension.short_name,
        );
        if (expDim) {
          if (!this.filters.includes(expDim.id)) {
            this.filters.push(expDim.id);
          }
          this.selectedDimValues[expDim.id] = df.allowed_value_ids;
          filteredDims.push(expDim.shortName);
        }
      }
      // show some info to the user
      if (filteredDims.length > 0) {
        this.showSnackbar({
          content: this.$t("view_applied", {
            view: view.short_name,
            dims: filteredDims.join(", "),
          }),
          color: "success",
        });
      }
    },
    saveDescription() {
      this.reportDescription = this.newReportDescription;
      this.showDescriptionDialog = false;
    },
    cancelDescriptionEdit() {
      this.showDescriptionDialog = false;
    },
    restoreStateFromUrl() {
      // Only restore if there are URL parameters
      if (Object.keys(this.$route.query).length === 0) {
        return;
      }

      const wasSetupInProgress = this.setupInProgress;
      this.setupInProgress = true;

      try {
        this.restoreTrackedState();
        if (this.explicitDims) {
          this.explicitDims.forEach((dim) => {
            if (!this.selectedDimValues[dim.id]) {
              this.selectedDimValues[dim.id] = [];
            }
          });
        }
      } catch (error) {
        console.warn("Failed to restore state from URL:", error);
      } finally {
        this.setupInProgress = wasSetupInProgress;
      }
    },
    restoreTrackedState() {
      if (this.reportId) {
        return;
      }
      try {
        this.trackedState = fromBase64Object(this.$route.query);
      } catch (error) {
        console.warn("Invalid URL parameters, using defaults:", error);
        this.showSnackbar({
          content: this.$t("invalid_url_parameters"),
          color: "warning",
        });
      }
    },
  },

  async mounted() {
    this.loading = true;
    this.setupInProgress = true;
    try {
      await this.fetchReportTypes();
      const hasUrlParams = Object.keys(this.$route.query).length > 0;
      if (this.reportId) {
        await this.fetchSettings();
      } else if (hasUrlParams) {
        this.restoreStateFromUrl();
      }
      if (this.selectedReportTypes.length === 0 && !hasUrlParams) {
        const defaultReport = this.allReportTypes.find(
          (rt) => rt.short_name === "TR",
        );
        if (defaultReport) {
          this.selectedReportTypes = [
            ...this.selectedReportTypes,
            defaultReport.pk,
          ];
          this.rows = ["platform"];
          if (this.organizationSelected) {
            this.filters.push("organization");
            this.selectedOrganizations = [this.globallySelectedOrganization.pk];
          }
          if (this.dateRangeStart) {
            this.filters.push("date");
            this.selectedDateRange.start = this.dateRangeStart;
          }
          if (this.dateRangeCoverageEnd) {
            if (!this.filters.includes("date")) {
              this.filters.push("date");
            }
            this.selectedDateRange.end = this.dateRangeCoverageEnd;
          }
          // this change has to be done after all watchers, etc. have run
          this.$nextTick(() => (this.columns = ["metric"]));
        }
      }
    } finally {
      this.loading = false;
      this.setupInProgress = false;
      this.$nextTick(() => {
        this.initialLoad = false;
      });
    }
  },

  watch: {
    possibleRows(newVal) {
      const newIds = newVal.map((dim) => dim.id);
      if (this.splitBy && !newIds.includes(this.splitBy)) {
        this.splitBy = null;
      }
      if (!this.setupInProgress && this.allReportTypes.length > 0) {
        this.columns = this.columns.filter((dim) => newIds.includes(dim));
      }
    },
    rows: {
      deep: true,
      handler(newRows, oldRows) {
        // Remove any selected rows from columns to avoid conflicts
        this.columns = this.columns.filter((dim) => !newRows.includes(dim));
        if (!this.setupInProgress) {
          // empty the tag class on row change to prevent unrelated class
          // from being used in filter
          this.selectedTagClass = null;
          if (!this.tagRollUpPossible) {
            this.tagRollUp = false;
          }
        }
        this.fetchAccessibleTags();
      },
    },
    splitBy() {
      if (this.splitBy) {
        this.columns = this.columns.filter((dim) => dim !== this.splitBy);
        // Remove splitBy from rows if it's selected
        if (this.rows.includes(this.splitBy)) {
          this.rows = this.rows.filter((row) => row !== this.splitBy);
          // If no rows left, select the first available one
          if (this.rows.length === 0) {
            const availableRow = this.possibleRows.find(
              (item) => item.id !== this.splitBy,
            );
            if (availableRow) {
              this.rows = [availableRow.id];
            }
          }
        }
      }
    },
    selectedReportTypes(newVal, oldVal) {
      if (isEqual(newVal, oldVal)) {
        return;
      }

      if (this.reportTypeSetOnLoad) {
        // first update after load should not do updates, but a new one should
        this.reportTypeSetOnLoad = false;
      } else if (!this.setupInProgress) {
        this.selectedDimValues = {};
        if (this.explicitDims) {
          // prepare the selectedDimValues array of the correct length
          this.explicitDims.forEach((dim) => {
            this.selectedDimValues[dim.id] = [];
            this.translators[dim.id] = this.translators.explicitDimension;
          });
        }

        // validate the primary dimensions to be compatible with the report types
        let newRows = this.rows.filter(this.isValidDim);
        // if at least one primary dimension is valid, use it
        if (newRows.length > 0) {
          this.rows = newRows;
        } else {
          // if no primary dimension is valid, use the first compatible dimension
          // which is not already in the columns and prefer platform if it is available
          const toTry = ["platform", ...this.possibleRows.map((dim) => dim.id)];
          for (let dim of toTry) {
            if (!this.columns.includes(dim)) {
              this.rows = [dim];
              break;
            }
          }
        }

        // validate filters for explicit dimensions - remove invalid ones
        this.filters = this.filters.filter((filter) => this.isValidDim(filter));
        this.columns = this.columns.filter((column) => this.isValidDim(column));
        if (this.splitBy && this.isValidDim(this.splitBy)) {
          this.splitBy = null;
        }
      }

      this.fetchCoverageData();
      this.reportViews = [];
      if (this.selectedReportTypes.length === 1) {
        this.fetchReportViews();
      }
      if (!this.showTitles) {
        this.filters = this.filters.filter((e) => e != "target");
      }
    },
    filters: {
      deep: true,
      handler(newValue, oldValue) {
        if (!this.setupInProgress) {
          for (let filter of oldValue) {
            if (!newValue.includes(filter)) {
              if (filter === "platform") {
                this.selectedPlatforms = [];
              } else if (filter === "organization") {
                this.selectedOrganizations = [];
              } else if (filter === "metric") {
                this.selectedMetrics = [];
              } else if (filter.startsWith("date")) {
                this.selectedDateRange = { start: null, end: null };
              } else if (filter.startsWith("dim")) {
                this.selectedDimValues[filter] = [];
              }
            }
          }
        }
      },
    },
    coverageDefiningUrlParams: {
      deep: true,
      handler(newValue, oldValue) {
        // because `deep` is true, we need to compare the values of newVal and
        // oldVal as the references might change without the actual value
        if (!isEqual(newValue, oldValue)) {
          // forget about export if the config has changed
          if (this.exportHandle) {
            this.exportHint = true;
          }
          this.exportHandle = null;
          // fetch new coverage data
          this.fetchCoverageData();
        }
      },
    },
    cannotShowZeroRows() {
      if (this.cannotShowZeroRows) this.showZeroRows = false;
    },
    trendMode() {
      if (this.trendMode) {
        // totals do not make sense with year over year
        this.showTotals = false;
        // turn on zero rows so that by default we show everything
        this.showZeroRows = true;
        // filtering by date with year over year does not make sense
        this.filters = this.filters.filter((f) => !f.startsWith("date"));
        // dates in rows also do not make sense
        this.rows = this.rows.filter((row) => !row.startsWith("date"));
        if (this.rows.length === 0) {
          this.rows = ["platform"];
        }
      } else {
        // turn zero rows off as they are not very useful outside of trend mode
        this.showZeroRows = false;
      }
    },
    tagRollUp() {
      // if we turn off tag roll up, we need to turn off the remainder
      if (!this.tagRollUp) {
        this.showRemainder = false;
      }
      // we want to invalidate the ordering because primary dimension
      // effectively changes with tag roll up
      this.orderBy = [];
    },
    showDescriptionDialog(newValue) {
      if (newValue === true) {
        this.newReportDescription = this.reportDescription;
      }
    },
    explicitDims: {
      handler(newDims) {
        newDims.forEach((dim, index) => {
          let dimName = `dim${index + 1}`;
          this.translators[dimName] = this.translators.explicitDimension;
        });
      },
      immediate: true,
    },
    "$route.query": {
      deep: true,
      handler(newQuery, oldQuery) {
        if (!this.setupInProgress && !isEqual(newQuery, oldQuery)) {
          const newState = fromBase64Object(newQuery);
          if (!this.reportId) {
            const currentState = this.trackedState;
            if (!isEqual(newState, currentState)) {
              this.restoreStateFromUrl();
            }
          }
        }
      },
    },
    shouldAutoRun(newVal) {
      if (newVal) {
        this.$nextTick(() => {
          this.runReport();
        });
      }
    },
    usesMultiIndex(newVal) {
      if (this.usesMultiIndex) {
        // switch off all things not compatible with multiindex
        this.tagRollUp = false;
        this.showZeroRows = false;
      }
    },
    canMergeReportTypes() {
      if (!this.canMergeReportTypes) {
        // reset to false if merge report types is not possible
        this.mergeReportTypes = false;
      }
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

.v-selection-control--density-comfortable {
  --v-selection-control-size: 40px;
}

.v-card-title {
  line-height: 2.5rem;
}
.extra-info {
  font-size: 0.75rem;
  font-weight: 300;
}
</style>
