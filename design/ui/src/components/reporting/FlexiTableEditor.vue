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
  unlock_tt: Unlock the report for editing.
  save_success: Report was successfully saved.
  report_title: Report title
  report_description: Report description
  please_fill_in_title: Please fill in report title and access level and hit 'Save changes' again.
  select_at_least_one_column_dim: At least one column dimension must be selected.
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
  coverage_base_tt: Data coverage in the base period.
  coverage_compared_tt: Data coverage in the compared period.
  coverage_title_tt: Data coverage shows how many months of data from a possible maximum are available for the selected report(s) and applied filters. Numbers below 100% indicate that some data is missing. Click on the number to go to a detailed breakdown.
  view_applied: View filters for '{view}' were applied to {dims}.
  metric_sum_warning_title: The configured report potentially sums several metrics together.
  metric_sum_warning_detail: This can lead to misleading results as metrics may overlap each other. To prevent this, add metric into columns or split-by, or add a metric filter with a single value.
  apply_standard_filters: Apply standard filters

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
  report_description: Popis reportu
  please_fill_in_title: Vyplňte prosím název reportu a úroveň přístupu výše a pak stiskněte tlačítko 'Uložit změny' znovu.
  select_at_least_one_column_dim: Musí být vybrán alespoň jeden rozměr, který definuje sloupce.
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
  coverage_base_tt: Pokrytí daty v základním období.
  coverage_compared_tt: Pokrytí daty v porovnávaném období.
  coverage_title_tt: Pokrytí daty ukazuje, kolik měsíců dat z možného maxima je k dispozici pro zvolené reporty a aplikované filtry. Číslo pod 100% značí, že některá data chybí. Kliknutí na číslo vás přenese na podrobný rozpis.
  view_applied: Filtry pro '{view}' byly aplikovány na {dims}.
  metric_sum_warning_title: Konfigurovaný report potenciálně sčítá několik metrik dohromady.
  metric_sum_warning_detail: To může vést k zavádějícím výsledkům, protože metriky se mohou překrývat. Řešením je přidání metriku do sloupců nebo split-by, nebo přidání filtru metrik s jedinou hodnotou.
  apply_standard_filters: Aplikovat standardní filtry
</i18n>

<template>
  <v-container fluid>
    <ReportLoadingWidget v-if="loading"></ReportLoadingWidget>
    <div v-else>
      <v-form>
        <v-row v-if="wantsSave">
          <v-col cols="8" md="5">
            <v-text-field
              :disabled="readOnly"
              v-model="reportName"
              class="font-weight-light text-h5"
              :label="$t('report_title')"
              :rules="wantsSave ? [rules.required] : []"
            ></v-text-field>
          </v-col>
          <v-col cols="8" md="5">
            <section class="d-flex align-center description_report">
              <v-dialog max-width="800" class="edit_description_dialog">
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
                    v-if="!readOnly || (readOnly && reportDescription)"
                    size="x-small"
                    v-bind="activatorProps"
                    :class="['ml-2 mt-3', readOnly ? 'disabled_icon' : '']"
                  >
                    fas fa-edit
                  </v-icon>
                </template>
                <template v-slot:default="{ isActive }">
                  <v-card :title="$t('report_description')">
                    <v-card-text>
                      <v-textarea
                        v-model="reportDescription"
                        class="font-weight-light text-h5"
                        :label="$t('report_description')"
                        :readonly="readOnly"
                        hide-details
                      ></v-textarea>
                    </v-card-text>
                    <v-card-actions>
                      <v-btn
                        variant="elevated"
                        :text="$t('actions.close')"
                        @click="isActive.value = false"
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
            ></AccessLevelSelector>
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
              item-title="name"
              multiple
              chips
              style="min-width: 265px"
              closable-chips
              class="report_type"
              :disabled="readOnly"
            ></v-autocomplete>
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
              item-title="name"
              style="min-width: 265px"
              item-value="id"
              :disabled="readOnly"
            ></v-select>
          </v-col>
          <v-col
            v-if="readOnly && canEdit"
            cols="auto"
            class="align-self-center"
          >
            <v-tooltip location="bottom">
              <template #activator="{ props }">
                <v-btn
                  elevation="2"
                  fab
                  size="small"
                  color="primary"
                  @click="edit = true"
                  v-bind="props"
                >
                  <v-icon size="small">fa fa-edit</v-icon>
                </v-btn>
              </template>
              {{ $t("unlock_tt") }}
            </v-tooltip>
          </v-col>
        </v-row>
        <v-row v-if="reportViews.length">
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
        <v-row>
          <v-col>
            <v-card class="pa-2">
              <v-card-title class="pt-2">{{ $t("labels.rows") }}</v-card-title>
              <v-card-text>
                <v-radio-group
                  v-model="watchedRow"
                  hide-details
                  class="mt-1"
                  density="compact"
                  :disabled="!reportTypeSelected || readOnly"
                >
                  <v-radio
                    v-for="row in possibleRows"
                    :label="row.name"
                    :key="row.id"
                    color="primary"
                    :disabled="
                      row.id === splitBy ||
                      (row.id.startsWith('date') && trendMode) ||
                      readOnly
                    "
                    :value="row.id"
                  ></v-radio>
                </v-radio-group>
              </v-card-text>
            </v-card>
          </v-col>
          <v-col>
            <v-card class="pa-2 fill-height">
              <v-card-title
                class="d-flex pt-2 justify-space-between align-start mb-1"
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
                      item.id === row ||
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
                            size="small"
                            variant="outlined"
                            color="secondary"
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
                            size="small"
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
        <v-row v-if="tagRollUpPossible">
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
        <v-row v-if="filters.length || coverageData">
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
                        v-if="filters.includes(`dim${index + 1}`)"
                      >
                        <FilterCard :title="ed.name">
                          <DimensionKeySelector
                            :query-url="selectorBaseUrl"
                            v-model="selectedDimValues[index]"
                            :dimension="`dim${index + 1}`"
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
                      :tooltip="$t('coverage_tt')"
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
        <v-row>
          <v-col v-if="!reportRunning" cols="auto">
            <v-tooltip location="bottom">
              <template #activator="{ props }">
                <v-btn
                  @click="runReport"
                  :disabled="!(formValid && hasGroupBy) || reportRunning"
                  v-bind="props"
                  min-width="12rem"
                  color="defaultButton"
                >
                  <v-icon size="small" color="green lighten-2" class="mr-1"
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
                  <v-icon size="small" color="red lighten-2" class="mr-1"
                    >fa fa-stop
                  </v-icon>
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
                  :disabled="!(formValid && hasGroupBy)"
                  color="defaultButton"
                >
                  <v-icon size="small" color="blue lighten-2" class="mr-1"
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
              v-if="!hasGroupBy && selectedReportTypes.length"
              variant="outlined"
              >{{ $t("select_at_least_one_column_dim") }}
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
          <v-col cols="auto" class="pt-0" v-if="!trendMode">
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
              :disabled="!(formValid && hasGroupBy)"
            >
              <v-icon class="mr-1" size="small">far fa-hdd</v-icon>
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
        ></FlexiTableOutput>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import axios from "axios";
import { mapActions, mapGetters, mapState } from "vuex";
import FromToMonthEntry from "@/components/util/FromToMonthEntry";
import FromToYearEntry from "@/components/util/FromToYearEntry";
import DimensionKeySelector from "@/components/selectors/DimensionKeySelector";
import ExportMonitorWidget from "@/components/util/ExportMonitorWidget";
import FlexiTableOutput from "@/components/reporting/FlexiTableOutput";
import translators from "@/mixins/translators";
import { dimensionMixin } from "@/mixins/dimensions";
import reportTypes from "@/mixins/reportTypes";
import { FlexiReport } from "@/libs/flexi-reports";
import ReportLoadingWidget from "@/components/reporting/ReportLoadingWidget";
import isEqual from "lodash/isEqual";
import AccessLevelSelector from "@/components/reporting/AccessLevelSelector";
import formRulesMixin from "@/mixins/formRulesMixin";
import {
  anyDateToYm,
  lastCoveredYearDate,
  parseDateTime,
  ymDateFormat,
  ymDateParse,
} from "@/libs/dates";
import cancellation from "@/mixins/cancellation";
import { toBase64JSON } from "@/libs/serialization";
import TagSelector from "@/components/tags/TagSelector";
import TagClassSelector from "@/components/tags/TagClassSelector";
import CoverageCard from "@/components/coverage/CoverageCard.vue";
import ReportNamingWidget from "@/components/reporting/ReportNamingWidget.vue";
import differenceInCalendarMonths from "date-fns/differenceInCalendarMonths";
import lastDayOfYear from "date-fns/lastDayOfYear";
import startOfYear from "date-fns/startOfYear";
import addYears from "date-fns/addYears";
import { useGoTo } from "vuetify";

import FilterCard from "@/components/reporting/FilterCard.vue";
import { explicitDimensions } from "@/libs/dimensions";

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
      selectedTitleTagClass: null,
      selectedPlatformTags: [],
      selectedOrganizationTags: [],
      selectedTagClass: null, // this one is for the tag roll-up, not the title tag class
      filterOrgsByTag: false,
      filterPlatformsByTag: false,
      filterTitlesByClass: false,
      trendMode: false,
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
      edit: !this.reportId || "edit" in this.$route.query,
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
      if (this.trendMode) {
        base = base.filter((d) => !d.id.startsWith("date"));
      }
      if (this.selectedReportTypes.length <= 1) {
        // only show report type if there is more than one selected
        base = base.filter((d) => d.id !== "report_type");
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
      // this is here just to watch for changes, it is not used directly
      // to make requests
      return {
        primary_dimension: this.row,
        filters: toBase64JSON(this.appliedFilters),
        groups: toBase64JSON(this.appliedGroups),
        zero_rows: this.showZeroRows,
        trend_mode: this.trendMode,
        base_period_filters: toBase64JSON(this.tmBaseDateRange),
        compared_period_filters: toBase64JSON(this.tmComparedDateRange),
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
      return this.columns.length > 0 || this.trendMode;
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
          (item) => item.pk === this.selectedReportTypes[0],
        );
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
      return this.allReportTypes.filter(
        (item) => this.selectedReportTypes.indexOf(item.pk) >= 0,
      );
    },
    reportObject() {
      let rt = new FlexiReport();
      rt.name = this.reportName;
      rt.description = this.reportDescription;
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
      rt.owner = this.owner;
      rt.ownerOrganization = this.ownerOrganization;
      rt.includeZeroRows = this.showZeroRows;
      rt.includeTotals = this.showTotals;
      rt.tagRollUp = this.tagRollUp;
      rt.tagClass = this.selectedTagClass?.pk;
      rt.showUntaggedRemainder = this.showRemainder;
      rt.trendMode = this.trendMode;
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
      return ["target", "platform", "organization"].includes(this.row);
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
    cannotShowZeroRows() {
      // if we sum by tag, we need to allow zero rows
      if (this.tagRollUp) return false;
      // in trend mode, we can show zero rows, because the meaning is different
      if (this.trendMode) return false;
      // if rows are organization or platform, we can show zero rows
      if (["organization", "platform"].includes(this.row)) return false;
      // for titles, we can only show zero rows if we have the titles
      // limited by a tag
      if (this.row === "target" && this.selectedTitleTags.length > 0)
        return false;
      // otherwise, we cannot show zero rows
      return true;
    },
    zeroRowsTooltip() {
      if (this.trendMode) {
        return this.$t("zero_rows_tooltip_trend_mode");
      }
      return this.$t("zero_rows_tooltip", {
        row: this.$t(this.row),
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
      if (this.row === "metric") return false;
      if (this.filters.includes("metric") && this.selectedMetrics.length === 1)
        return false;
      return true;
    },
    reportDescriptionClass() {
      return this.readOnly ? "text-grey-lighten-1" : "";
    },
  },

  methods: {
    // goTo() {
    //   return goTo;
    // },
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
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
      // used when only sorting is changed, nothing else
      await this.$refs.outputTable.updateOutput(this.reportObject);
    },
    async runExport(format) {
      if (!this.formValid) {
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
    async firstSave(name, description, access) {
      this.reportName = name;
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
      if (!this.formValid) {
        return;
      }
      if (this.canGetData) {
        try {
          // update order by based on the current state of output table
          this.updateOrderByFromOutputTable();
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
      if (config.filters) {
        // deal with report_type first as it influences much more later
        let rt_filter = config.filters.find(
          (item) => item.dimension === "report_type",
        );
        if (rt_filter) {
          this.reportTypeSetOnLoad = true;
          this.selectedReportTypes = rt_filter.values;
          this.selectedDimValues = [];
          if (this.selectedReportTypes.length === 1) {
            let rt = this.allReportTypes.find(
              (item) => item.pk === this.selectedReportTypes[0],
            );
            if (rt) {
              rt.dimensions_sorted.forEach(() =>
                this.selectedDimValues.push([]),
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
      if (this.selectedReportTypes.length && this.coverageGaugeCount > 0)
        this.coverageData = await this.reportObject.getCoverage();
    },
    goToCoverageOverview() {
      this.$router.push({
        name: "data-coverage-overview",
        query: {
          rtid:
            this.selectedReportTypes.length === 1
              ? this.selectedReportTypes[0]
              : undefined,
        },
      });
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
        this.selectedDimValues[index] = [];
        if (this.filters.includes(dim)) {
          this.filters = this.filters.filter((item) => item !== dim);
        }
      });
      // apply filters to explicit dimensions
      for (let df of view.dimension_filters) {
        let expDim = this.explicitDims.findIndex(
          (dim) => dim.shortName === df.dimension.short_name,
        );
        if (expDim >= 0) {
          const ref = this.explicitDims[expDim].ref;
          if (!this.filters.includes(ref)) {
            this.filters.push(ref);
          }
          this.selectedDimValues[expDim] = df.allowed_value_ids;
          filteredDims.push(this.explicitDims[expDim].shortName);
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
        const defaultReport = this.allReportTypes.find(
          (rt) => rt.short_name === "TR",
        );
        if (defaultReport) {
          this.selectedReportTypes = [
            ...this.selectedReportTypes,
            defaultReport.pk,
          ];
          this.row = "platform";
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
    }
  },

  watch: {
    // possibleRows(newVal) {
    //   if (this.splitBy && !newVal.includes(this.splitBy)) {
    //     this.splitBy = null;
    //   }
    // },
    row() {
      this.columns = this.columns.filter((dim) => dim !== this.row);
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
    splitBy() {
      this.columns = this.columns.filter((dim) => dim !== this.splitBy);
      if (this.row === this.splitBy) {
        this.row = this.possibleRows.find(
          (item) => item.id !== this.splitBy,
        ).id;
      }
    },
    selectedReportTypes() {
      if (this.reportTypeSetOnLoad) {
        // first update after load should not do updates, but a new one should
        this.reportTypeSetOnLoad = false;
      } else {
        this.selectedDimValues = [];
        if (this.explicitDims) {
          // prepare the selectedDimValues array of the correct length
          this.explicitDims.forEach((dim, index) => {
            this.selectedDimValues.push([]);
            let dimName = `dim${index + 1}`;
            this.translators[dimName] = this.translators.explicitDimension;
          });
        }
        // remove groups that are for explicit dimensions
        explicitDimensions.forEach((dim) => {
          this.columns = this.columns.filter((item) => item !== dim);
        });
      }
      this.fetchCoverageData();
      this.reportViews = [];
      if (this.selectedReportTypes.length === 1) {
        this.fetchReportViews();
      }
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
        this.row = this.row.startsWith("date") ? "platform" : this.row;
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

.disabled_icon {
  opacity: 0.7;
}

.v-selection-control--density-comfortable {
  --v-selection-control-size: 40px;
}

.v-chip.v-chip--size-small {
  padding: 0 12px;
}

.v-card-title {
  line-height: 2.5rem;
}
.extra-info {
  font-size: 0.75rem;
  font-weight: 300;
}
</style>
