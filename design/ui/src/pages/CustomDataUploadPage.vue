<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<i18n lang="yaml" src="@/locales/sources.yaml"></i18n>

<i18n lang="yaml" src="@/locales/dialog.yaml"></i18n>

<i18n lang="yaml">
en:
  description: |
    On this page, you can upload data for platforms which do not offer a SUSHI interface,
    older data which are no longer available through SUSHI or for non-COUNTER platforms.
  data_file: Data file to upload
  data_file_placeholder: Upload a file containing data.
  dismiss: Dismiss
  step_method: Select method
  step_upload: Data upload
  step_preflight: Check before data import
  step_done: Imported data view
  input_rows: Read input data rows
  overview: Overview
  upload: Upload
  tab_chart: Chart
  tab_data: Data
  finish_import: Finish import
  confirm: Confirm
  report_type: Report type
  thats_all: That is all. The data were imported.
  return_to_platform: Go to platform page
  upload_more_files: Upload more files
  preflight_error_found: Error occurred during data check
  multiple_report_types_found: Multiple report types were found in provided file. It is possible to upload only one report type at a time. Please modify the input data so that only one report type is present (e.g. by uploading only a single sheet in xlsx).
  import_error_found: The following error was found when data were imported
  back_to_start: Back to data upload
  organization_from_data: No organization is selected. Organization will be derived from data.
  missing_organization_in_data: Data does not contain organization. Please select the organization for which you are importing data from the page toolbar.
  need_to_unset_organization: The uploaded file contains explicit organization column. The currently selected organization will be ignored when importing data.
  clashing_import_batches_title: Can't import data
  clashing_import_batches_text: Imported file contains data for dates for which there already are existing records in the database. To import this file you need to delete the existing data first.
  delete_existing: Delete existing
  regenerate_preflight: Regenerate overview
  preflight_data_outdated: Preflight data are outdated, please regenerate preflight.
  errors:
    requires_utf8: It seems that the provided file uses unsupported encoding. Please check that the file is encoded using UTF-8.
    unsupported_file_format: File format .{format} is not supported, please convert it to .csv or .xlsx.
    no_parser_found: "Sorry, but we cannot detect the format of the uploaded file. If you send us the report to ask{'@'}celus.net, we will check it and try to teach CELUS to process it correctly."
    unknown_report_type: "We were able to process the file, but we could not determine the report type for storage. Please let us know at ask{'@'}celus.net to fix the problem."
    no_organization_selected: No organization found in data. You need to select organization manually.
    counter_header_not_found: Counter header was not found in data.
    unrecognized_report_name: Unrecognized counter report name found in data '{crn}'.
    unrecognized_report_id: Unrecognized counter report ID found in data '{crid}'.
    unknown_counter_error: "Something went wrong and CELUS was not able to process the data. CELUS is pretty good at processing COUNTER reports, but some publishers extend them in a way that CELUS does not understand. If you send us the report to ask{'@'}celus.net, we will check it and try to teach CELUS to process it correctly."
    unknown_raw_error: "Something went wrong and CELUS was not able to process the data. Parsing non-COUNTER data is tough because there is no standard and even reports from one publisher may change from year to year. If you send us the report to ask{'@'}celus.net, we will check it and try to teach CELUS to process it correctly."
    unknown_error: "An unknown error has occurred during data processing. If you send us the report to ask{'@'}celus.net, we will check it and try to teach CELUS to process it correctly."
    xls_error: Unable to parse .xls file. Please try to convert the file to .xlsx
    unsupported_report_type: Detected report type "{rt}" is not currently supported.
    whitelisting_error: This report type was not whitelisted for this platform because we could not verify that it is consistent with other reports on the platform. Contact your administrator to whitelist this report type for this platform.
  unauthorized_multiple_org_title: Unauthorized to import
  unauthorized_multiple_org_text: This file contains data for multiple organizations and only consortial admin is allowed to import it.
  no_non_counter_for_platform: This platform does not support non-counter data.
  method_counter_label_name: COUNTER
  method_counter_label_text: Use this method to import data from COUNTER table and JSON reports.
  method_raw_label_name: Raw non-COUNTER data
  method_raw_label_text: Upload a non-COUNTER report as you received it from the publisher. CELUS will try to automatically detect the format.
  method_celus_label_name: CELUS non-COUNTER custom format
  method_celus_label_text: Upload data prepared in the custom CELUS format for non-COUNTER data.
  method_celus_disabled_tt: There are no non-COUNTER reports defined for this platform.
  method_raw_disabled_tt: There are no raw reports supported for this platform.
  method_changed_to_counter: The processing method was updated, because the provided file is in standard COUNTER format.
  notes_url_description: Check our {link} for more information about the expected report file format for this platform.
  notes_url_href: support web
  extra_info: Extra information
  sheet: Sheet
  before_preflight_text: The following information was extracted from the uploaded file. Please check that it looks correct before continuing.
  metadata_info: The following metadata were extracted from the header of the uploaded report.
  report_type_info: Report structure
  report_type_info_desc: The following report structure is expected for the uploaded file.

cs:
  description: |
    Tato stránka umožňuje nahrání dat k platformám, které neposkytují rozhraní SUSHI,
    starších dat, která již nejsou na platformě v rámci SUSHI k dispozici, nebo pro ne-COUNTER platformy.
  data_file: Datový soubor k nahrání
  data_file_placeholder: Nahrajte soubor, který obsahuje data.
  dismiss: Zavřít
  step_method: Vyberte metodu
  step_upload: Nahrání dat
  step_preflight: Kontrola před importem
  step_done: Zobrazení importovaných dat
  input_rows: Načtené datové řádky
  overview: Přehled
  upload: Nahrát
  tab_chart: Graf
  tab_data: Data
  finish_import: Dokončit import
  confirm: Potvrdit
  report_type: Typ reportu
  thats_all: To je vše. Data byla úspěšně importována.
  return_to_platform: Přejít na stránku platformy
  upload_more_files: Nahrát další data
  preflight_error_found: Chyba při kontrole dat
  multiple_report_types_found: V souboru bylo nalezeno víc typů reportů. Je možné nahrát pouze jeden typ reportu z jednoho souboru. Prosím změnte soubor tak, aby v něm byl pouze jeden typ reportu (např. tak, že budete nahrávat xlsx soubor s jedním listem).
  import_error_found: Při nahrávání dat byla nalezena následující chyba
  back_to_start: Zpět na nahrání dat
  organization_from_data: Organizace nebyla vybrána a bude odvozena ze vstupních dat.
  missing_organization_in_data: Data neobsahují informace o organizaci. Prosím vyberte organizaci, pro kterou nahráváte data, z menu v horní liště.
  need_to_unset_organization: Soubor obsahuje sloupec s explicitně uvedenou organizací. Aktuálně vybraná organizace bude při importu dat ignorována.
  clashing_import_batches_title: Není možné naimportovat data
  clashing_import_batches_text: Nahrávaný soubor obsahuje data za období, pro které jsou již v databázi uložena data. Pro nahrání souboru je třeba nejprve existující data smazat.
  delete_existing: Smazat existující
  regenerate_preflight: Přegenerovat přehled
  preflight_data_outdated: Data přehledu již nejsou platná. Prosím přegenerujte přehled.
  errors:
    requires_utf8: Zdá se, že nahraný soubor obsahuje nepodorované kódování. Prosím ověřte, že je soubor zakódován pomocí UTF-8.
    unsupported_file_format: Typ souboru .{format} není podporovaný, prosím konvertujte jej do .csv nebo .xlsx.
    no_parser_found: "Omlouváme se, ale nepodařilo se rozpoznat formát nahraného souboru. Pokud nám soubor pošlete na ask{'@'}celus.net, zkontrolujeme ho a pokusíme se CELUS naučit, jak ho zpracovat."
    unknown_report_type: "Soubor se podařilo načíst, ale nemůžeme určit typ reportu pro uložení. Napište nám na ask{'@'}celus.net a my problém vyřešíme."
    no_organization_selected: Organizace nelze vyčíst z dat. Vyberte prosím organizaci manuálně.
    counter_header_not_found: Nebyla nalezena hlavička counter dat.
    unrecognized_report_name: V datech se nachází neznámé jméno typu reportu '{crn}'.
    unrecognized_report_id: V datech se nachází neznámé ID typu reportu '{crid}'.
    unknown_counter_error: "Něco se pokazilo a CELUS nebyl schopen data zpracovat. CELUS je poměrně dobrý v zpracování COUNTER reportů, ale někteří vydavatelé je rozšiřují způsobem, kterému CELUS nerozumí. Pokud nám report pošlete na ask{'@'}celus.net, zkontrolujeme ho a pokusíme se CELUS naučit, jak ho zpracovat."
    unknown_raw_error: "Něco se pokazilo a CELUS nebyl schopen data zpracovat. Zpracování ne-COUNTER dat je složité, protože neexistuje žádný standard a dokonce i reporty od jednoho vydavatele se mohou z roku na rok měnit. Pokud nám report pošlete na ask{'@'}celus.net, zkontrolujeme ho a pokusíme se CELUS naučit, jak ho zpracovat."
    unknown_error: "Při zpracování dat došlo k neznámé chybě. Pokud nám report pošlete na ask{'@'}celus.net, zkontrolujeme ho a pokusíme se CELUS naučit, jak ho zpracovat."
    xls_error: Nedaří se zpracovat .xls soubor. Prosím zkuste soubor zkonvertovat na .xlsx
    unsupported_report_type: Zjištěný typ reportu "{rt}" není v současné době podporován.
    whitelisting_error: Tento typ reportu nebyl povolen pro tuto platformu, protože nebylo možné ověřit, že je konzistentní s ostatními reporty na platformě. Kontaktujte prosím svého administrátora, aby povolil tento typ reportu pro tuto platformu.
  unauthorized_multiple_org_title: Neautorizovaný import
  unauthorized_multiple_org_text: Tento soubor obsahuje data pro více organizací a pouze konzorciální admin může nahrávat data pro více organizací z jednoho souboru.
  no_non_counter_for_platform: Tato platforma nepodporuje formáty mimo counter.
  method_counter_label_name: COUNTER
  method_counter_label_text: Použijte tuto metodu pro import dat v tabulkovém COUNTER formátu a ve formě JSON reportu.
  method_raw_label_name: Surová ne-COUNTER data
  method_raw_label_text: ne-COUNTER report je nahrán v takovém formátu, v jakém jste ho obdrželi od vydavatele. CELUS se pokusí automaticky detekovat formát dat.
  method_celus_label_name: CELUS formát pro ne-COUNTER data
  method_celus_label_text: Nahraná data jsou připravena ve vlastním formátu, který CELUS používá pro ne-COUNTER data.
  method_celus_disabled_tt: Pro tuto platformu nejsou definovány žádné non-COUNTER reporty.
  method_raw_disabled_tt: Pro tuto platformu nejsou surové reporty podporované.
  method_changed_to_counter: Metoda nahrávání byla pozměněna, protože nahraný soubor je ve standardním COUNTER formátu.
  notes_url_description: Pro ověření správnosti nahrávaného souboru zkontrolujte prosím naše {link} pro tuto platformu.
  notes_url_href: stránky podpory
  extra_info: Extra informace
  sheet: List
  before_preflight_text: Následující informace byly extrahovány z nahraného souboru. Prosím zkontrolujte, že jsou data správná, než budete pokračovat.
  metadata_info: Následující metadata byla extrahována z hlavičky nahraného reportu.
  report_type_info: Struktura reportu
  report_type_info_desc: Následující struktura reportu je očekávána pro nahraný soubor.
</i18n>

<template>
  <div class="px-2">
    <v-container fluid>
      <v-row>
        <v-breadcrumbs :items="breadcrumbs" class="pl-0">
          <template v-slot:item="props">
            <router-link
              v-if="props.item.linkName"
              :to="{ name: props.item.linkName, params: props.item.linkParams }"
            >
              {{ props.item.text }}
            </router-link>
            <span v-else>
              {{ props.item.text }}
            </span>
          </template>
        </v-breadcrumbs>
      </v-row>
      <v-row>
        <v-col v-if="platform">
          <ItemBadge
            :item="platform"
            tag="h2"
            class="d-flex align-center"
            :badge-class="'badge_manual'"
            :badge-inline="true"
          ></ItemBadge>
        </v-col>
      </v-row>
      <v-row>
        <v-col>
          <p v-html="$t('description')"></p>
        </v-col>
      </v-row>
    </v-container>
    <v-sheet
      v-if="globalSpinnerOn"
      class="justify-center"
      elevation="1"
      width="100%"
    >
      <v-skeleton-loader
        type="list-item-avatar-three-line, list-item-avatar-three-line, list-item-avatar-three-line"
      ></v-skeleton-loader>
    </v-sheet>
    <v-stepper-vertical hide-actions v-model="step" v-else>
      <template v-slot:default="{ step }">
        <v-stepper-vertical-item
          :complete="step > steps.method"
          :title="
            method && step > steps.method
              ? $t('step_method') +
                '(' +
                $t('method_' + method + '_label_name') +
                ')'
              : $t('step_method')
          "
          :value="steps.method"
        >
          <v-sheet class="pa-2 pt-0">
            <v-radio-group
              v-model="method"
              :hide-details="true"
              color="primary"
            >
              <v-radio value="counter">
                <template #label>
                  <strong class="font-weight-black">{{
                    $t("method_counter_label_name")
                  }}</strong
                  >:
                  <span class="pl-1">{{
                    $t("method_counter_label_text")
                  }}</span>
                </template>
              </v-radio>
              <v-radio
                value="raw"
                :readonly="!canImportRawData"
                v-if="isRawImportEnabled"
              >
                <template #label>
                  <span>
                    <span :class="canImportRawData ? '' : 'text-disabled'">
                      <strong class="font-weight-black">{{
                        $t("method_raw_label_name")
                      }}</strong
                      >:
                      <span class="pl-1">{{
                        $t("method_raw_label_text")
                      }}</span>
                    </span>
                    <v-tooltip location="bottom" v-if="!canImportRawData">
                      <template #activator="{ props }">
                        <v-icon v-bind="props" size="x-small" color="info"
                          >fa fa-info-circle</v-icon
                        >
                      </template>
                      <span>{{ $t("method_raw_disabled_tt") }}</span>
                    </v-tooltip>
                  </span>
                </template>
              </v-radio>
              <v-radio
                value="celus"
                :readonly="!canImportCelusFormat"
                v-if="allowCelusFormatImport"
              >
                <template #label>
                  <span>
                    <span :class="canImportCelusFormat ? '' : 'text-disabled'">
                      <strong class="font-weight-black">{{
                        $t("method_celus_label_name")
                      }}</strong
                      >:
                      <span class="pl-1">{{
                        $t("method_celus_label_text")
                      }}</span>
                      <v-tooltip location="bottom" v-if="!canImportCelusFormat">
                        <template #activator="{ props }">
                          <v-icon v-bind="props" size="small" color="info"
                            >fa fa-info-circle</v-icon
                          >
                        </template>
                        <span>{{ $t("method_celus_disabled_tt") }}</span>
                      </v-tooltip>
                    </span>
                  </span>
                </template>
              </v-radio>
            </v-radio-group>
          </v-sheet>
          <template v-slot:actions="{ next }">
            <v-btn
              @click="next"
              :disabled="!method"
              variant="elevated"
              class="ml-4"
              color="primary"
            >
              {{ $t("continue") }}
            </v-btn>
          </template>
          <template v-slot:prev> </template>
        </v-stepper-vertical-item>
        <v-stepper-vertical-item
          :complete="step > steps.upload"
          :title="$t('step_upload')"
          :value="steps.upload"
        >
          <v-form ref="form" v-model="valid" v-if="!uploadObjectId">
            <v-container fluid class="pb-5 pt-0">
              <v-row v-if="notesUrl">
                <v-col>
                  <v-alert type="info" variant="tonal" text>
                    <i18n-t keypath="notes_url_description">
                      <template #link>
                        <a :href="notesUrl" target="_blank">{{
                          $t("notes_url_href")
                        }}</a>
                      </template>
                    </i18n-t>
                  </v-alert>
                </v-col>
              </v-row>
              <v-row>
                <v-col>
                  <CustomUploadInfoWidget :method="method" />
                </v-col>
              </v-row>
              <v-row>
                <v-col cols="12" md="6" v-if="canSelectReportType">
                  <v-select
                    v-model="selectedReportType"
                    :items="reportTypesToSelect"
                    item-title="name"
                    item-value="pk"
                    required
                    return-object
                    :label="$t('labels.report_type')"
                    :rules="[filledIn]"
                    :loading="!reportTypesFetched"
                  >
                    <template v-slot:item="{ props, item }">
                      <v-tooltip
                        v-bind="props"
                        location="bottom"
                        max-width="600px"
                        v-if="badge(item)"
                      >
                        <template #activator="{ props }">
                          <v-badge
                            inline
                            :content="$t(badge(item).content)"
                            :color="badge(item).color"
                          >
                            <template v-slot:badge>
                              <span v-bind="props">{{
                                $t(badge(item).content)
                              }}</span>
                            </template>
                          </v-badge>
                        </template>
                        <span>{{ $t(badge(item).tooltip) }}</span>
                      </v-tooltip>
                    </template>
                  </v-select>
                </v-col>
                <v-col cols="12" md="6">
                  <v-file-input
                    v-model="dataFile"
                    :rules="[filledIn]"
                    prepend-icon="fa fa-table"
                    variant="underlined"
                    show-size
                    :label="$t('data_file')"
                    :placeholder="$t('data_file_placeholder')"
                    required
                    accept=".csv, .json, .tsv, .xlsx, .xls"
                  >
                  </v-file-input>
                </v-col>
              </v-row>
              <v-row no-gutters class="pt-2">
                <v-col cols="12">
                  <ReportTypeInfoWidget
                    v-if="
                      method === 'celus' &&
                      selectedReportType &&
                      selectedReportType.pk &&
                      canSelectReportType
                    "
                    :report-type="selectedReportType"
                    outlined
                  ></ReportTypeInfoWidget>
                </v-col>
              </v-row>
              <v-row>
                <v-alert
                  type="warning"
                  class="d-flex"
                  v-if="!$store.getters.organizationSelected"
                >
                  {{ $t("organization_from_data") }}
                </v-alert>
              </v-row>
            </v-container>
          </v-form>
          <v-form v-else-if="uploadObject" class="pb-2">
            <v-row>
              <v-col class="font-weight-light">{{
                $t("before_preflight_text")
              }}</v-col>
            </v-row>
            <v-row>
              <v-col>
                <table class="overview">
                  <tr>
                    <th class="pb-6">{{ $t("labels.report_type") }}</th>
                    <td class="pb-6">{{ uploadObject.report_type.name }}</td>
                  </tr>
                  <tr v-if="method === 'raw'">
                    <th class="align-top">
                      {{ $t("report_type_info") }}
                      <div class="caption pt-3" style="max-width: 10rem">
                        {{ $t("report_type_info_desc") }}
                      </div>
                    </th>
                    <td>
                      <ReportTypeInfoWidget
                        :report-type="uploadObject.report_type"
                        hide-implicit-dimensions
                        hide-title
                        is-raw
                      ></ReportTypeInfoWidget>
                    </td>
                  </tr>
                  <tr v-if="perSheetExtras && perSheetExtras.length > 0">
                    <th class="align-top">
                      {{ $t("labels.metadata") }}
                      <div class="caption pt-3" style="max-width: 10rem">
                        {{ $t("metadata_info") }}
                      </div>
                    </th>
                    <td>
                      <v-card class="pa-2">
                        <v-tabs
                          v-model="extraTab"
                          v-show="perSheetExtras.length > 1"
                        >
                          <v-tab
                            v-for="(data, sheet_idx) in perSheetExtras"
                            :key="`extra-${sheet_idx}`"
                            :model-value="sheet_idx"
                            >{{ `${$t("sheet")} ${sheet_idx + 1}` }}
                          </v-tab>
                        </v-tabs>
                        <v-tabs-window v-model="extraTab">
                          <v-tabs-window-item
                            v-for="[sheet_idx, data] in perSheetExtras"
                            :key="`extra-${sheet_idx}`"
                            :model-value="sheet_idx"
                          >
                            <v-table density="compact">
                              <template v-slot:default>
                                <tbody>
                                  <tr
                                    v-for="(value, key) in data"
                                    :key="`extra-${sheet_idx}-${key}`"
                                  >
                                    <th class="th_table">{{ key }}</th>
                                    <v-list v-if="Array.isArray(value)">
                                      <v-list-item
                                        v-for="(line, idx) in value"
                                        :key="`extra-${sheet_idx}-${key}-${idx}`"
                                      >
                                        {{ line }}
                                      </v-list-item>
                                    </v-list>
                                    <td v-else class="td_table">{{ value }}</td>
                                  </tr>
                                </tbody>
                              </template>
                            </v-table>
                          </v-tabs-window-item>
                        </v-tabs-window>
                      </v-card>
                    </td>
                  </tr>
                </table>
              </v-col>
            </v-row>
            <v-row>
              <v-col> </v-col>
            </v-row>
          </v-form>
          <template v-slot:actions="{ next, prev }">
            <v-btn
              v-if="!uploadObjectId"
              @click="prev"
              color="defaultButton"
              variant="elevated"
              >{{ $t("back") }}</v-btn
            >
            <v-btn
              v-else-if="uploadObject"
              class="mr-2"
              variant="elevated"
              color="defaultButton"
              @click="backToStart(), prev"
            >
              {{ $t("back_to_start") }}
            </v-btn>
            <v-btn
              @click="postData"
              :disabled="!canUpload || !dataFile"
              :loading="uploading"
              variant="elevated"
              color="primary"
              v-if="!uploadObjectId"
              class="ml-4"
              >{{ $t("upload") }}</v-btn
            >
            <v-progress-linear
              class="ma-3"
              v-model="uploadProgress"
              round
              v-if="uploading"
            ></v-progress-linear>
            <v-btn
              v-else-if="canConfirm && uploadObject && uploadObjectId"
              @click="confirmReportType(), next"
              color="primary"
              :loading="confirming"
              class="ml-4"
            >
              <v-icon size="small" class="mr-2">fas fa-caret-right</v-icon>
              {{ $t("continue") }}
            </v-btn>
          </template>
        </v-stepper-vertical-item>
        <v-stepper-vertical-item
          :complete="step > steps.preflight"
          :title="$t('step_preflight')"
          :value="steps.preflight"
        >
          <template v-slot:header>
            {{ $t("step_preflight") }}
          </template>
          <v-card>
            <v-card-title>{{ $t("overview") }}</v-card-title>
            <v-card-text>
              <LargeSpinner
                v-if="state === 'confirmed' || spinnerOn || !state"
              ></LargeSpinner>
              <v-alert
                v-else-if="state === 'preflight' && !preflightDataFormatValid"
                type="warning"
              >
                <span v-text="$t('preflight_data_outdated')"></span>
              </v-alert>
              <ImportPreflightDataWidget
                v-else-if="state === 'preflight'"
                :preflight-data="preflightData"
                :interest-metrics="selectedInterestMetrics"
                :usable-metrics="usableMetrics"
                :check-metrics="checkMetrics"
                :raw-disabled-per-organization="rawDisabledPerOrganization"
                :auto-create-metrics="automaticallyCreateMetrics"
                :metrics="metrics"
                :method="method"
              ></ImportPreflightDataWidget>
              <v-alert v-else-if="state === 'prefailed'" type="error">
                <h3 v-text="$t('preflight_error_found')" class="pb-2"></h3>
                <div
                  bg-color="error"
                  @click="expand = !expand"
                  class="expand_trans"
                >
                  <div class="expand_trans_sub">
                    <strong v-if="error === 'unicode-decode'">
                      {{ $t("errors.requires_utf8") }}
                    </strong>
                    <strong v-else-if="error === 'nibbler'">
                      {{ nibblerReason(errorDetails.nibbler) }}
                    </strong>
                    <strong
                      v-else-if="
                        error === 'multiple-report-type' ||
                        error === 'unknown-report-type'
                      "
                    >
                      {{ $t("errors.unknown_report_type") }}
                    </strong>
                    <strong v-else-if="error === 'no-organization-selected'">
                      {{ $t("errors.no_organization_selected") }}
                    </strong>
                    <strong v-else>
                      {{ unknownErrorMessage }}
                    </strong>
                  </div>
                  <v-icon>{{
                    expand ? "fa fa-chevron-up" : "fa fa-chevron-down"
                  }}</v-icon>
                </div>
                <v-expand-transition>
                  <pre
                    v-text="errorDetails.exception"
                    v-if="errorDetails && errorDetails.exception"
                    class="pt-2 expand_panel"
                    v-show="expand"
                  ></pre>
                </v-expand-transition>
              </v-alert>
              <v-alert
                v-else-if="
                  preflightData && preflightData.clashing_months.length
                "
                type="warning"
                class="mt-2 mb-1"
              >
                <strong v-text="$t('clashing_import_batches_title')"></strong>:
                <span v-text="$t('clashing_import_batches_text')"></span>
              </v-alert>
              <v-alert
                v-if="!hasImportPermission"
                type="warning"
                class="mt-2 mb-1"
              >
                <strong v-text="$t('unauthorized_multiple_org_title')"></strong
                >:
                <span v-text="$t('unauthorized_multiple_org_text')"></span>
              </v-alert>
              <v-alert
                type="warning"
                class="ma-4"
                v-if="missingOrgInData && state === 'preflight'"
              >
                {{ $t("missing_organization_in_data") }}
              </v-alert>
              <v-alert
                type="info"
                variant="tonal"
                class="ma-4"
                v-if="needToUnsetOrg"
              >
                {{ $t("need_to_unset_organization") }}
              </v-alert>
            </v-card-text>
            <v-card-actions v-if="state === 'preflight'">
              <v-btn
                v-if="
                  preflightData &&
                  preflightDataFormatValid &&
                  preflightData.clashing_months.length &&
                  !this.wrongOrganizations.length > 0 &&
                  !this.rawDisabledPerOrganization.length > 0
                "
                variant="elevated"
                color="warning"
                @click="showConfirmDeleteDialog = true"
              >
                <v-icon size="small" class="mr-2">fa fa-trash-alt</v-icon>
                {{ $t("delete_existing") }}
              </v-btn>
              <v-btn
                @click="backToStart()"
                variant="elevated"
                color="defaultButton"
                >{{ $t("back_to_start") }}</v-btn
              >
              <v-btn
                v-if="canImport"
                variant="elevated"
                @click="triggerImportData()"
                color="primary"
                class="pulse"
                :loading="state === 'importing' || importing"
                :disabled="
                  (preflightData && !!preflightData.clashing_months.length) ||
                  preflighting
                "
              >
                <v-icon size="small" class="mr-2">fa fa-gears</v-icon>
                {{ $t("finish_import") }}
              </v-btn>
              <v-btn
                v-else
                color="primary"
                variant="elevated"
                @click="regeneratePreflight"
                :disabled="importing"
              >
                <v-icon size="small" class="mr-6">fas fa-redo</v-icon>
                {{ $t("regenerate_preflight") }}
              </v-btn>
            </v-card-actions>
            <v-card-actions v-else-if="state === 'prefailed'">
              <v-btn
                color="primary"
                @click="regeneratePreflight"
                :disabled="importing"
                variant="elevated"
              >
                <v-icon size="small" class="mr-6">fas fa-redo</v-icon>
                {{ $t("regenerate_preflight") }}
              </v-btn>
              <v-btn
                @click="backToStart()"
                variant="elevated"
                color="defaultButton"
                >{{ $t("back_to_start") }}</v-btn
              >
            </v-card-actions>
          </v-card>
        </v-stepper-vertical-item>
        <v-stepper-vertical-item
          :complete="step > steps.done"
          :title="$t('step_done')"
          :value="steps.done"
        >
          <v-card>
            <v-card-text v-if="state === 'imported'">
              <v-tabs v-model="tab" dark bg-color="primary" fixed-tabs>
                <v-tab
                  :class="{
                    'tab-active': tab === 'chart',
                    'tab-inactive': tab !== 'chart',
                  }"
                  value="chart"
                  >{{ $t("tab_chart") }}</v-tab
                >
                <v-tab
                  :class="{
                    'tab-active': tab === 'data',
                    'tab-inactive': tab !== 'data',
                  }"
                  value="data"
                  >{{ $t("tab_data") }}</v-tab
                >
              </v-tabs>
              <v-tabs-window v-model="tab">
                <v-tabs-window-item value="chart">
                  <MDUChart :mdu-id="uploadObject.pk"></MDUChart>
                </v-tabs-window-item>
                <v-tabs-window-item value="data">
                  <AccessLogList
                    :mdu-id="uploadObject.pk"
                    :show-organization="multipleOrganizations"
                  ></AccessLogList>
                </v-tabs-window-item>
              </v-tabs-window>
              <v-container fluid>
                <v-row>
                  <v-col cols="auto" class="align-self-center">
                    <v-icon color="success" size="small"
                      >fa fa-check-circle</v-icon
                    >
                    {{ $t("thats_all") }}
                  </v-col>
                  <v-spacer></v-spacer>
                  <v-col cols="auto">
                    <v-btn
                      :to="{
                        name: 'platform-detail',
                        params: { platformId: platformId },
                      }"
                      color="secondary"
                    >
                      {{ $t("return_to_platform") }}
                    </v-btn>
                  </v-col>
                  <v-col cols="auto">
                    <v-btn @click="backToStart()" color="primary">{{
                      $t("upload_more_files")
                    }}</v-btn>
                  </v-col>
                </v-row>
              </v-container>
            </v-card-text>
            <v-card-text v-else-if="state === 'failed'">
              <v-container>
                <v-row>
                  <v-col cols="auto">
                    <v-alert type="error">
                      <h3 v-text="$t('import_error_found')" class="pb-2"></h3>
                      <strong>{{ unknownErrorMessage }}</strong>
                      <pre
                        v-text="errorDetails.exception"
                        v-if="errorDetails && errorDetails.exception"
                        class="pt-2"
                      ></pre>
                    </v-alert>
                  </v-col>
                </v-row>
                <v-row>
                  <v-col cols="auto">
                    <v-btn @click="backToStart()" color="primary">{{
                      $t("upload_more_files")
                    }}</v-btn>
                  </v-col>
                </v-row>
              </v-container>
            </v-card-text>
            <v-card-text v-else>
              <LargeSpinner></LargeSpinner>
            </v-card-text>
          </v-card>
        </v-stepper-vertical-item>
      </template>
    </v-stepper-vertical>
    <v-dialog max-width="1100px" v-model="showConfirmDeleteDialog">
      <ImportBatchesDeleteConfirm
        v-model="showConfirmDeleteDialog"
        v-if="showConfirmDeleteDialog"
        :import-batch-slices="slicesToDelete"
        @cancel="showConfirmDeleteDialog = false"
        @deleted="deletePerformed()"
      ></ImportBatchesDeleteConfirm>
    </v-dialog>
    <ErrorDialog
      v-if="showErrorDialog"
      v-model="showErrorDialog"
      :errors="errors"
    ></ErrorDialog>
  </div>
</template>

<script>
import axios from "axios";
import { mapActions, mapGetters, mapState } from "vuex";
import AccessLogList from "@/components/AccessLogList";
import LargeSpinner from "@/components/util/LargeSpinner";
import CustomUploadInfoWidget from "@/components/CustomUploadInfoWidget";
import ReportTypeInfoWidget from "@/components/ReportTypeInfoWidget";
import ImportBatchesDeleteConfirm from "@/components/ImportBatchesDeleteConfirm";
import ImportPreflightDataWidget from "@/components/ImportPreflightDataWidget";
import { counterHeaderRepr } from "@/libs/counter_header.js";
import MDUChart from "@/components/MDUChart";
import ErrorDialog from "@/components/util/ErrorDialog";
import isEmpty from "lodash/isEmpty";
import ItemBadge from "@/components/util/ItemBadge";
import {
  VStepperVertical,
  VStepperVerticalItem,
} from "vuetify/labs/VStepperVertical";

export default {
  name: "CustomDataUploadPage",
  components: {
    ErrorDialog,
    MDUChart,
    ImportBatchesDeleteConfirm,
    ImportPreflightDataWidget,
    LargeSpinner,
    AccessLogList,
    CustomUploadInfoWidget,
    ReportTypeInfoWidget,
    ItemBadge,
    VStepperVertical,
    VStepperVerticalItem,
  },
  props: {
    platformId: { required: true },
    uploadObjectId: { required: false },
  },
  data() {
    return {
      dataFile: null,
      valid: false,
      platform: null,
      panel: null,
      reportTypes: [],
      reportTypesFetched: false,
      metrics: [],
      metricsFetched: false,
      organizations: [],
      organizationsFetched: false,
      selectedReportType: null,
      showErrorDialog: false,
      showConfirmDeleteDialog: false,
      errors: [],
      expand: false,
      // filledIn: [(value) => !!value || "File must be filled in"],
      step: 1,
      uploadObject: null,
      tab: "chart",
      refreshTimeout: null,
      spinnerOn: false,
      globalSpinnerOn: true,
      uploading: false,
      importing: false,
      preflighting: false,
      confirming: false,
      uploadProgress: 0,
      steps: {
        method: 1,
        upload: 2,
        preflight: 3,
        done: 4,
      },
      method: "counter",
      methodChanged: false,
      extraTab: null,
    };
  },
  computed: {
    ...mapState({
      organizationId: "selectedOrganizationId",
    }),
    ...mapGetters({
      allowCelusFormatImport: "allowCelusFormatImport",
      automaticallyCreateMetrics: "automaticallyCreateMetrics",
      showManagementStuff: "showManagementStuff",
      enableRawDataImport: "enableRawDataImport",
      isRawImportEnabled: "isRawImportEnabled",
    }),
    perSheetExtras() {
      if (!this.uploadObject?.extra) {
        return null;
      }
      return Object.entries(this.uploadObject.extra)
        .filter((tuple) => !isEmpty(tuple[1]))
        .map(([idx, extras]) =>
          this.method === "counter"
            ? [idx, counterHeaderRepr(extras)]
            : [idx, extras],
        );
    },
    breadcrumbs() {
      return [
        {
          text: this.$t("pages.platforms"),
          linkName: "platform-list",
        },
        {
          text: this.platform === null ? "" : this.platform.name,
          linkName: "platform-detail",
          linkParams: {
            platformId: this.platformId,
          },
        },
        {
          text: this.$t("actions.upload_data"),
        },
      ];
    },
    selectedInterestMetrics() {
      if (this.uploadObject && this.uploadObject.report_type) {
        return this.uploadObject.report_type.interest_metric_set.map(
          (item) => item.metric.short_name,
        );
      }
      return [];
    },
    usableMetrics() {
      if (this.uploadObject && this.uploadObject.report_type) {
        if (this.uploadObject.report_type.controlled_metrics) {
          return this.metrics
            .filter((metric) =>
              this.uploadObject.report_type.controlled_metrics.includes(
                metric.pk,
              ),
            )
            .map((item) => item.short_name);
        } else {
          return this.metrics.map((metric) => metric.short_name);
        }
      }
      return [];
    },
    multipleOrganizations() {
      return !!this.preflightData?.organizations;
    },
    slicesToDelete() {
      if (
        this.preflightData &&
        this.platformId &&
        this.organizationId &&
        this.uploadObject
      ) {
        if (this.wrongOrganizations.length > 0) {
          // can't delete when there are wrong organizations in data
          return null;
        }
        if (this.rawDisabledPerOrganization.length > 0) {
          // can't delete when data can't be reimported
          return null;
        }
        // There are several organizations in the data file
        return Object.entries(this.clashingMonthsPerOrg).map(
          ([org_id, months]) => ({
            platform: this.platformId,
            organization: org_id,
            report_type: this.uploadObject.report_type.pk,
            months: months,
          }),
        );
      }
      return [];
    },
    errorDetails() {
      if (this.uploadObject) {
        return this.uploadObject.error_details;
      } else {
        return null;
      }
    },
    missingOrgInData() {
      if (
        parseInt(this.organizationId) < 0 &&
        !this.preflightData?.organizations
      ) {
        return true;
      } else {
        return false;
      }
    },
    checkRawPerOrgPermission() {
      if (this.method == "raw") {
        return this.rawDisabledPerOrganization.length === 0;
      } else {
        return true;
      }
    },
    needToUnsetOrg() {
      if (
        !!this.uploadObject?.organization &&
        this.uploadObject?.state === "preflight" &&
        !!this.uploadObject?.preflight?.organizations
      ) {
        return true;
      }
      return false;
    },
    canImport() {
      if (this.uploadObject) {
        return (
          this.uploadObject.can_import &&
          !this.missingOrgInData &&
          this.checkRawPerOrgPermission &&
          Object.keys(this.preflightData?.months || {}).length > 0
        );
      }
      return false; // not uploaded yet
    },
    canConfirm() {
      if (this.uploadObject?.state === "initial") {
        return true;
      }
      return false; // not uploaded yet
    },
    canUpload() {
      return this.valid;
    },
    wrongOrganizations() {
      if (this.preflightData?.organizations) {
        return Object.keys(this.preflightData.organizations).filter(
          (name) => !this.preflightData.organizations[name].pk,
        );
      } else {
        return [];
      }
    },
    rawDisabledPerOrganization() {
      if (this.preflightData?.organizations) {
        const ids = Object.values(this.preflightData.organizations)
          .filter((o) => !!o.pk)
          .map((e) => e.pk);
        return this.organizations.filter(
          (o) => ids.includes(o.pk) && !o.is_raw_data_import_enabled,
        );
      } else {
        return [];
      }
    },
    hasImportPermission() {
      if (this.preflightData?.organizations) {
        return this.showManagementStuff;
      } else {
        // no multiple organizations in preflight
        return true;
      }
    },
    error() {
      if (this.uploadObject) {
        return this.uploadObject.error;
      } else {
        return null;
      }
    },
    state() {
      if (this.uploadObject) {
        return this.uploadObject.state;
      } else {
        return null;
      }
    },
    preflightDataFormatValid() {
      if (this.uploadObject) {
        return this.uploadObject.preflight.format_version === "5";
      } else {
        return false;
      }
    },
    checkMetrics() {
      if (this.uploadObject) {
        return this.uploadObject.report_type.controlled_metrics.length > 0;
      } else {
        return false;
      }
    },
    preflightData() {
      if (this.uploadObject) {
        let result = JSON.parse(JSON.stringify(this.uploadObject.preflight));
        result.clashing_months = this.uploadObject.clashing_months || [];
        result.can_import = this.uploadObject.can_import || false;
        return result;
      } else {
        return null;
      }
    },
    canSelectReportType() {
      return this.method === "celus";
    },
    notesUrl() {
      if (this.method === "raw") {
        return this.platform?.knowledgebase?.notes_url;
      }
      return null;
    },
    reportTypesToSelect() {
      switch (this.method) {
        case "celus":
          return this.reportTypes.filter((e) => !e.counter_report_type);
        case "counter":
          return this.reportTypes.filter((e) => !!e.counter_report_type);
        default:
          return [];
      }
    },
    canImportCelusFormat() {
      return !!this.reportTypes.find((e) => !e.counter_report_type);
    },
    canImportRawData() {
      return this.platform?.has_raw_parser;
    },
    currentOrganization() {
      if ((this.organizationId || -1) > 0) {
        const organizations = this.organizations.filter(
          (e) => e.pk === this.organizationId,
        );
        return organizations.length > 0 ? organizations[0] : null;
      } else {
        return null;
      }
    },
    unknownErrorMessage() {
      switch (this.method) {
        case "raw":
          return this.$t("errors.unknown_raw_error");
        case "counter":
          return this.$t("errors.unknown_counter_error");
        default:
          return this.$t("errors.unknown_error");
      }
    },
    privatePlaformForOrganizationPk() {
      return this.platform?.source?.organization?.pk;
    },
    dataFileExt() {
      if (this.dataFile) {
        return this.dataFile.name.split(".").pop();
      }
      return null;
    },
    clashingMonthsPerOrg() {
      let mapping = {};
      for (const rec of this.preflightData?.clashing_months || []) {
        mapping[rec.org_id] = (mapping[rec.org_id] || []).concat([rec.month]);
      }
      return mapping;
    },
  },
  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
      changeForceDisableOrganizationSelector:
        "changeForceDisableOrganizationSelector",
      selectOrganization: "selectOrganization",
    }),
    filledIn(v) {
      if (v === null) return "File must be filled in";
      return true;
    },

    setProgress(total, current) {
      if (total) {
        this.uploadProgress = (100 * current) / total;
      }
    },
    async postData() {
      let formData = new FormData();
      formData.append("data_file", this.dataFile);
      if (parseInt(this.organizationId) > 0) {
        formData.append("organization", this.organizationId);
      }
      formData.append("platform", this.platformId);
      if (this.canSelectReportType) {
        formData.append("report_type_id", this.selectedReportType.pk);
      }
      formData.append("method", this.method);

      this.uploading = true;
      this.uploadProgress = 0;
      this.showErrorDialog = false;
      try {
        let response = await axios.post("/api/manual-data-upload/", formData, {
          headers: { "Content-Type": "multipart/form-data" },
          onUploadProgress: (e) => this.setProgress(e.total, e.loaded),
        });
        this.uploadObject = response.data;

        // Method could be updated
        if (this.method != this.uploadObject.method) {
          if (this.step == this.steps.upload) {
            this.methodChanged = true;
            this.showSnackbar({
              content: this.$t(`method_changed_to_${this.uploadObject.method}`),
              color: "warning",
            });
          }
          this.method = this.uploadObject.method;
        } else {
          this.methodChanged = false;
        }

        await this.$router.push({
          name: "platform-upload-data-step-preflight",
          params: {
            uploadObjectId: this.uploadObject.pk,
            platformId: this.platformId,
          },
        });
      } catch (error) {
        if (error.response?.status === 400) {
          let info = error.response.data;
          if ("data_file" in info) {
            this.showErrorDialog = true;
            this.errors = info.data_file;
          } else if ("nibbler_errors" in info) {
            this.showErrorDialog = true;
            this.errors = info.nibbler_errors.map((e) =>
              this.nibblerErrorText(e),
            );
          } else if ("encoding_error" in info) {
            this.showErrorDialog = true;
            this.errors = [this.$t("errors.requires_utf8")];
          } else if ("wrong_file_format" in info) {
            this.showErrorDialog = true;
            this.errors = [
              this.$t("errors.unsupported_file_format", {
                format: this.dataFileExt,
              }),
            ];
          } else if ("xls_error" in info) {
            this.showErrorDialog = true;
            this.errors = [this.$t("errors.xls_error")];
          } else if ("multiple_report_types" in info) {
            this.handleMultipleReportTypeError();
          } else if ("unsupported_report_type" in info) {
            this.showErrorDialog = true;
            this.errors = [
              this.$t("errors.unsupported_report_type", {
                rt: info.unsupported_report_type[0],
              }),
            ];
          } else if ("whitelisting_error" in info) {
            this.showErrorDialog = true;
            this.errors = [this.$t("errors.whitelisting_error")];
          } else {
            this.showSnackbar({ content: "Error sending data: " + error });
          }
        } else {
          this.showSnackbar({ content: "Error sending data: " + error });
        }
      } finally {
        this.uploading = false;
        this.uploadProgress = 0;
      }
    },
    async loadPlatform() {
      if (this.organizationId) {
        try {
          let response = await axios.get(
            `/api/organization/${this.organizationId}/all-platform/${this.platformId}/`,
          );
          this.platform = response.data;
        } catch (error) {
          this.showSnackbar({
            content: "Error loading platform details: " + error,
          });
        }
      }
    },
    async loadReportTypes() {
      let url = `/api/organization/${this.organizationId}/all-platform/${this.platformId}/report-types/`;
      try {
        const response = await axios.get(url);

        this.reportTypes = response.data.sort((a, b) =>
          a.name.localeCompare(b.name),
        );
        if (this.$route.query?.report_type_id) {
          let rt_id = parseInt(this.$route.query.report_type_id);
          if (rt_id) {
            this.selectedReportType = this.reportTypesToSelect.find(
              (rt) => rt.pk === rt_id,
            );
          }
        }

        // Select default report type
        this.selectedReportType ?? this.reportTypes.length > 0
          ? this.reportTypesToSelect[0]
          : null;

        this.reportTypesFetched = true;
      } catch (error) {
        this.showSnackbar({
          content: "Error loading report types: " + error,
        });
      }
    },
    async loadOrganizations() {
      let url = `/api/organization/`;
      try {
        const response = await axios.get(url);
        this.organizations = response.data;
        this.organizationsFetched = true;
      } catch (error) {
        this.showSnackbar({ content: "Error loading organizations: " + error });
      }
    },
    async loadMetrics() {
      let url = `/api/metric/`;
      try {
        const response = await axios.get(url);
        this.metrics = response.data;
        this.metricsFetched = true;
      } catch (error) {
        this.showSnackbar({ content: "Error loading metrics: " + error });
      }
    },
    async triggerImportData() {
      if (this.uploadObject && !this.importing && this.canImport) {
        this.importing = true;
        let url = `/api/manual-data-upload/${this.uploadObject.pk}/import-data/`;
        try {
          await axios.post(url, {});
        } catch (error) {
          this.showSnackbar({ content: "Error processing data: " + error });
        } finally {
          this.importing = false;
        }
        // reload object
        await this.loadMdu();
      }
    },
    async regeneratePreflight() {
      if (
        this.uploadObject &&
        !this.preflighting &&
        ["preflight", "prefailed"].includes(this.uploadObject.state)
      ) {
        this.preflighting = true;
        let url = `/api/manual-data-upload/${this.uploadObject.pk}/preflight/`;
        let data = this.currentOrganization
          ? { organization_id: this.currentOrganization.pk }
          : {};
        try {
          await axios.post(url, data);
        } catch (error) {
          this.showSnackbar({
            content: "Error triggering preflight generation: " + error,
          });
        } finally {
          this.preflighting = false;
        }
        // reload object
        this.spinnerOn = true;
        this.loadMdu();
      }
    },
    async confirmReportType() {
      if (this.uploadObject?.state === "initial") {
        this.confirming = true;
        let url = `/api/manual-data-upload/${this.uploadObject.pk}/confirm/`;
        try {
          await axios.post(url);
        } catch (error) {
          this.showSnackbar({
            content: "Error can't confirm report type: " + error,
          });
        } finally {
          this.confirming = false;
        }
        // reload object
        this.spinnerOn = true;
        this.loadMdu();
      }
    },
    async loadMdu() {
      this.cancelRefreshTimeout();

      // Try to fetch metrics
      if (!this.metricsFetched) {
        await this.loadMetrics();
      }

      if (this.uploadObjectId) {
        try {
          let response = await axios.get(
            `/api/manual-data-upload/${this.uploadObjectId}/`,
          );
          this.uploadObject = response.data;

          switch (this.uploadObject.state) {
            case "initial":
              this.step = this.steps.upload;
              break;
            case "confirmed":
            case "prefailed":
              this.step = this.steps.preflight;
              break;
            case "preflight":
              // Auto regenarete outdated preflights
              if (!this.preflightDataFormatValid) {
                this.regeneratePreflight();
              }
              this.step = this.steps.preflight;
              break;
            case "importing":
            case "imported":
            case "failed":
              this.step = this.steps.done;
              break;
          }
          if (["confirmed", "importing"].includes(this.uploadObject.state)) {
            this.cancelRefreshTimeout();
            this.refreshTimeout = setTimeout(() => this.loadMdu(), 5000); // every 5 seconds
          }
        } catch (error) {
          this.showSnackbar({ content: "Error loading upload data: " + error });
        } finally {
          this.spinnerOn = false;
        }
      }
    },
    cancelRefreshTimeout() {
      if (this.refreshTimeout) {
        clearTimeout(this.refreshTimeout);
        this.refreshTimeout = null;
      }
    },
    async backToStart() {
      let reportTypeId = this.uploadObject?.report_type?.pk;
      this.dataFile = null;
      this.step = this.steps.upload;
      await this.$router.push({
        name: "platform-upload-data",
        params: {
          platformId: this.platformId,
        },
        query: {
          report_type_id: reportTypeId,
          method: this.method,
        },
      });
    },
    deletePerformed() {
      this.showConfirmDeleteDialog = false;
      // regenerate preflight
      this.regeneratePreflight();
    },
    async loadRequiredData() {
      // report type API call is quite time consuming
      // so waiting for it to finish would be inconvenient
      // loading attribute in v-select is used instead
      this.loadReportTypes();
      this.loadOrganizations();
      await Promise.all([this.loadMetrics(), this.loadPlatform()]);
      this.globalSpinnerOn = false;
    },
    nibblerErrorText(error) {
      const sheet_idx = error.sheet_idx;
      const parsers_info = error.parsers_info;
      let prefix = "";
      if (sheet_idx != null) {
        let readable_sheet_idx = parseInt(sheet_idx) + 1;
        prefix = `${this.$t("sheet")} ${readable_sheet_idx}: `;
      }
      if (this.method === "counter") {
        // Missing counter header
        if (
          Object.values(parsers_info).every((e) =>
            e.some((ee) =>
              [
                "no-header-data-extracted",
                "report-name-not-in-header",
              ].includes(ee.code),
            ),
          )
        ) {
          return prefix + this.$t("errors.counter_header_not_found");
        }

        // Check For Wrong Report_ID of C5 reports
        for (const [parser_name, data] of Object.entries(parsers_info)) {
          if (parser_name.startsWith("static.counter5")) {
            for (const record of data) {
              if (record.code === "wrong-report-type") {
                return (
                  prefix +
                  this.$t("errors.unrecognized_report_id", {
                    crid: record.found,
                  })
                );
              }
            }
          }
        }

        // Check For Wrong Report name of C4 reports
        for (const [parser_name, data] of Object.entries(parsers_info)) {
          if (parser_name.startsWith("static.counter4")) {
            for (const record of data) {
              if (record.code === "wrong-report-type") {
                return (
                  prefix +
                  this.$t("errors.unrecognized_report_name", {
                    crn: record.found,
                  })
                );
              }
            }
          }
        }
      }
      return prefix + this.nibblerReason([error]);
    },
    nibblerReason(errors) {
      if (errors.every((e) => e.name.startsWith("NoParser"))) {
        return this.$t("errors.no_parser_found");
      }
      return this.unknownErrorMessage;
    },
    handleMultipleReportTypeError() {
      this.showErrorDialog = true;
      this.errors = [this.$t("multiple_report_types_found")];
    },
  },
  async mounted() {
    await this.loadRequiredData();
    if (this.$route.query.method) {
      // Check whether this method can be set
      if (
        this.$route.query.method === "raw" &&
        this.currentOrganization &&
        !this.currentOrganization.is_raw_data_import_enabled
      ) {
        // choose method again
        this.method = "counter";
        this.step = this.steps.method;
      } else {
        this.method = this.$route.query.method;
        this.step = this.steps.upload;
      }
    }
    if (this.uploadObjectId && this.step === this.steps.upload) {
      // If object is present move to preflight step
      this.step = this.steps.preflight;
    }
    if (this.uploadObjectId) {
      await this.loadMdu();
      this.method = this.uploadObject.method;
    }
  },
  beforeUnmount() {
    this.cancelRefreshTimeout();
  },
  watch: {
    platform() {
      let hide = !!this.privatePlaformForOrganizationPk;
      this.changeForceDisableOrganizationSelector({
        hide: hide,
        route: this.$router.currentRoute.value.name,
      });
      // set organization when no organization is selected for private platform
      if (!this.currentOrganization && hide) {
        this.selectOrganization({ id: this.privatePlaformForOrganizationPk });
      }
    },
    organizationId() {
      this.regeneratePreflight();
      // Choose method again if selected organization can't import raw data
      if (
        this.step === this.steps.upload &&
        this.method === "raw" &&
        this.currentOrganization &&
        !this.currentOrganization.is_raw_data_import_enabled
      ) {
        this.method = "counter";
        this.step = this.steps.method;
      }
    },
    method() {
      if (this.reportTypesToSelect.length > 0) {
        this.selectedReportType = this.reportTypesToSelect[0];
      } else {
        this.selectedReportType = null;
      }
    },
  },
};
</script>

<style scoped>
strong {
  line-height: 1.25rem;
  font-weight: 500;
}
.th_table {
  font-size: 12px;
  font-weight: 700 !important;
}

.expand_trans {
  display: flex;
  align-items: center;
  padding: 16px 24px;
  cursor: pointer;
}

.expand_trans_sub {
  margin-right: 25px;
}

.expand_panel {
  padding: 0 24px;
}

.text-disabled {
  opacity: 0.9;
}

.td_table {
  word-break: break-word;
}

:deep(.v-stepper-vertical-item__avatar.v-avatar) {
  background-color: #2d5854 !important;
}
</style>
