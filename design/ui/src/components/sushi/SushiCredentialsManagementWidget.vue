<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<i18n lang="yaml" src="@/locales/dialog.yaml"></i18n>

<i18n lang="yaml" src="@/locales/sushi.yaml"></i18n>

<i18n lang="yaml">
en:
  add_new: Add new SUSHI
  export_selected: Export Selected
  export_selected_tooltip: Exports all the credentials you selected by using checkboxes.
  import: Import
  import_tooltip: Import credentials
  is_locked: These credentials are locked.
  is_unlocked: These credentials are not locked, you may edit them.
  cannot_edit: You cannot edit them.
  can_edit: Because of your privileges, you can still edit them.
  can_lock: You may lock/unlock these credentials - click to do so.
  test_checked: Harvest
  test_checked_tooltip: Opens a dialog for one-off harvesting of data for all selected SUSHI credentials.
  test_dialog: Manual SUSHI harvesting
  is_broken: |
    These credentials have been marked as broken because of harvesting failures.
    Automatic harvesting was postponed until the credentials are manually fixed.
  no_credentials_selected: No credentials selected
  no_broken_credentials_selected: No broken credentials selected
  no_clonable_credentials_selected: No clonable credentials selected
  there_are_no_credentials: There are no credentials
  select_at_least_one_credentials: Please select at least one set of SUSHI credentials using the checkboxes in the credentials list.
  select_at_least_one_broken_credentials: Please select at least one set of broken SUSHI credentials using the checkboxes in the credentials list.
  select_at_least_one_clonable_credentials: Please select at least one SUSHI credentials which can be cloned using the checkboxes in the credentials list.
  unverified_tooltip: No data has been obtained yet using the current version of these credentials. Please verify the credentials by manually harvesting some data.
  warn_same_credentials_in_org_tooltip: The same credentials are used for a different platform as well. This is likely an error and will cause data duplication.
  warn_same_credentials_global_tooltip: The same credentials are used by another organization. This is likely an error and will cause data duplication.
  first_add_some_credentials: You have not added any SUSHI credentials yet, please first add credentials using button above.
  import_credentials_confirm_title: Automatic import under construction
  import_credentials_confirm_text_1: CELUS currently doesn't support fully automatic importing of credentials, but we can load them up for you!
  import_credentials_confirm_text_2: Please, insert the credentials you would like to import into our prefilled Excel template (download it by clicking on the button below. Don't worry, the file contains detailed explanation on how to fill it correctly). Send the filled out file to
  import_credentials_confirm_text_3: with the subject line
  import_credentials_confirm_text_4: You can contact us at the same e-mail if you have any questions or issues with the template.
  download_file: Download template file
  set_last_harvestable_month: Set last harvestable month
  set_last_harvestable_month_tooltip: When you know that data for certain platforms is not available before a specific date, you can set this date here.
  last_harvestable_month_filter:
    all: All
    set: Set
    not_set: Not set
  bulk_actions: Bulk actions
  potential_issues:
    label: Potential issues
    broken: Broken credentials
    not_validated: Unverified credentials
    can_update: Possible to clone to 5.1
    can_update_verified: Safe to clone to 5.1
    duplicated: Duplicated
  potential_issues_tt:
    broken: Credentials marked as broken due to harvesting failures
    not_validated: No data has been harvested yet using these credentials - manual harvesting is required to verify them
    can_update: All COUNTER 5 credentials which can be cloned to COUNTER 5.1
    can_update_verified: COUNTER 5 credentials which can be cloned to COUNTER 5.1 and platform is known to support COUNTER 5.1
    duplicated: Same credentials are used multiple times
  last_updated_tooltip: Credentials were last updated by {user} on {time}.
  report_types_derived_from_platform_set: Report types are used from platform for selected credentials.

cs:
  add_new: Přidat nové SUSHI
  export: Exportuj
  export_selected: Exportovat vybrané
  export_selected_tooltip: Vyexportuje všechny přístupové údaje, které jste vybrali zaškrtnutím políčka.
  import: Importuj
  import_tooltip: Importovat přístupové údaje
  is_locked: Tyto přístupové údaje jsou uzamčené.
  is_unlocked: Tyto přístupové údaje nejsou uzamčené, můžete je editovat
  cannot_edit: Nemůžete je editovat.
  can_edit: Vaše oprávnění Vám umožňují je přesto editovat.
  can_lock: Kliknutím můžete tyto údaje uzamknout/odemknout.
  test_checked: Stáhni
  test_checked_tooltip: Otevře dialog pro jednorázové stažení dat pro všechny vybrané přístupové údaje SUSHI.
  test_dialog: Manuální stahování SUSHI
  is_broken: |
    Tyto přihlašovací údaje byly označeny jako nefunkční, kvůli neúspěchům při stahování. Automatické stahování
    bylo pozastaveno do doby než budou údaje ručně opraveny.
  no_credentials_selected: Nejsou vybrány žádné přihlašovací údaje
  no_broken_credentials_selected: Nejsou vybrány žádné nefunkční přihlašovací údaje
  no_clonable_credentials_selected: Nejsou vybrány žádné klonovatelné přihlašovací údaje
  there_are_no_credentials: Nemáte uloženy žádné přihlašovací údaje
  select_at_least_one_credentials: Vyberte prosím alespoň jedny přihlašovací údaje pomocí zaškrtávacích polí v seznamu přihlašovacích údajů.
  select_at_least_one_broken_credentials: Vyberte prosím alespoň jedny nefunkční přihlašovací údaje pomocí zaškrtávacích polí v seznamu přihlašovacích údajů.
  select_at_least_one_clonable_credentials: Vyberte prosím alespoň klonovatelné přihlašovací údaje pomocí zaškrtávacích polí v seznamu přihlašovacích údajů.
  unverified_tooltip: Žádná data zatím nebyla stažena se současnou verzí těchto přístupových údajů. Ověřte prosím platnost přihlašovacích údajů manuálním stažením dat.
  warn_same_credentials_in_org_tooltip: Stejné přístupové údaje jsou použity i u jiné platformy. Jde pravděpodobně o chybu, která způsobí duplikaci dat.
  warn_same_credentials_global_tooltip: Stejné přístupové údaje jsou použity jinou organizací. Jde pravděpodobně o chybu, která způsobí duplikaci dat.
  first_add_some_credentials: Nepřidali jste žádné SUSHI přihlašovací údaje, prosím nejprve přidejte přihlačovací údaje tlačítkem výše.
  import_credentials_confirm_title: Automatický import ve vývoji
  import_credentials_confirm_text_1: CELUS momentálně neimportuje přihlašovací údaje automaticky, ale můžete je naimportovat hromadně!
  import_credentials_confirm_text_2: Prosím, vyplňte přihlačovací údaje, které chcete importovat, do námi předvyplněného Excel souboru (stáhnete jej kliknutím na tlačítko níže. Nemějte obavy, soubor obsahuje detailní vysvětlení o tom, jak vyplnit tabulku správně). Zašlete vyplněný soubor na
  import_credentials_confirm_text_3: s předmětem
  import_credentials_confirm_text_4: Můžete nás kontaktovat na této e-mail adrese i pokud budete mít jakékoliv dotazy nebo problémy s tabulkou.
  download_file: stáhnout soubor
  set_last_harvestable_month: Nastavit poslední stáhnutelný měsíc
  set_last_harvestable_month_tooltip: Pokud víte, že data pro určité platformy nejsou dostupná před určitým datem, můžete toto datum nastavit zde.
  last_harvestable_month_filter:
    all: Vše
    set: Nastaven
    not_set: Nenastaven
  bulk_actions: Hromadné akce
  potential_issues:
    label: Potenciální problémy
    broken: Nefunkční přístupové údaje
    not_validated: Neověřené přístupové údaje
    can_update: Lze naklonovat do 5.1
    can_update_verified: Bezpečné klonování do 5.1
    duplicated: Duplicitní
  potential_issues_tt:
    broken: Přístupové údaje označené jako nefunkční kvůli chybám při stahování
    not_validated: Zatím nebyla stažena žádná data pomocí těchto přístupových údajů - je třeba je ověřit ručním stažením dat
    can_update: Všechny COUNTER 5 přístupové údaje, které lze naklonovat do COUNTER 5.1
    can_update_verified: COUNTER 5 přístupové údaje, které lze naklonovat do COUNTER 5.1 a platforma má ověřenou podporu COUNTER 5.1
    duplicated: Stejné přístupové údaje jsou použity vícekrát
  last_updated_tooltip: Přístupové údaje byly naposledy upraveny uživatelem {user} dne {time}.
  report_types_derived_from_platform_set: Typy reportů jsou odvozeny od platformy pro vybrané přístupové údaje.
</i18n>

<template>
  <v-container fluid>
    <v-card>
      <v-card-title>
        <v-container fluid>
          <v-row>
            <v-col cols="auto" align-self="center">
              <v-btn @click="activateCreateDialog" color="primary">
                <v-icon size="small" class="mr-2">fa fa-plus</v-icon>
                {{ $t("add_new") }}
              </v-btn>
            </v-col>
            <v-col cols="auto" align-self="center">
              <v-tooltip location="bottom">
                <template #activator="{ props }">
                  <v-btn
                    @click="testChecked('showTestDialog')"
                    color="secondary"
                    v-bind="props"
                  >
                    <v-icon size="small" class="mr-2">fa fa-download</v-icon>
                    {{ $t("test_checked") }}
                    <v-badge color="white" inline>
                      <template #badge>
                        <span class="text-success">{{
                          checkedCredentials.length
                        }}</span>
                      </template>
                    </v-badge>
                  </v-btn>
                </template>
                {{ $t("test_checked_tooltip") }}
              </v-tooltip>
            </v-col>
            <v-spacer></v-spacer>
            <v-col cols="auto">
              <v-tooltip location="bottom">
                <template #activator="{ props }">
                  <v-btn
                    @click="triggerCloneToNewer"
                    color="info"
                    v-bind="props"
                  >
                    <v-icon size="small" class="mr-2"
                      >far fa-arrow-alt-circle-up</v-icon
                    >
                    {{ $t("sushi.clone_to_newer.button") }}
                    <v-badge color="white" inline>
                      <template #badge>
                        <span class="text-info">{{
                          checkedUpdatableCredentials.length
                        }}</span>
                      </template>
                    </v-badge>
                  </v-btn>
                </template>
                {{ $t("sushi.clone_to_newer.tooltip") }}
              </v-tooltip>
            </v-col>
            <v-col cols="auto" align-self="center">
              <v-tooltip location="top">
                <template #activator="{ props }">
                  <v-btn
                    v-bind="props"
                    color="defaultButton"
                    @click="showImportCredentialsModal"
                  >
                    <v-icon size="small" class="mr-2"
                      >fas fa-file-import</v-icon
                    >
                    {{ $t("import") }}
                  </v-btn>
                </template>
                {{ $t("import_tooltip") }}
              </v-tooltip>
            </v-col>
            <v-col cols="auto" align-self="center">
              <v-tooltip location="top">
                <template #activator="{ props: tooltipProps }">
                  <v-menu offset-y>
                    <template #activator="{ props: menuProps }">
                      <v-btn
                        v-bind="{ ...menuProps, ...tooltipProps }"
                        color="defaultButton"
                        :loading="moreActionsLoading"
                      >
                        <v-icon size="small" class="mr-2"
                          >fa fa-layer-group</v-icon
                        >
                        {{ $t("bulk_actions") }}
                      </v-btn>
                    </template>
                    <v-list>
                      <v-tooltip location="bottom" max-width="600px">
                        <template #activator="{ props }">
                          <v-list-item
                            @click="
                              testChecked('showLastHarvestableMonthDialog')
                            "
                            v-bind="props"
                            :disabled="
                              checkedCredentials.length === 0 ||
                              moreActionsLoading
                            "
                          >
                            <v-list-item-title>
                              <v-icon
                                class="mr-2"
                                size="small"
                                color="lighterIcons"
                              >
                                far fa-calendar-alt</v-icon
                              >
                              {{ $t("set_last_harvestable_month") }}
                              <v-badge color="secondary" inline class="mt-1">
                                <template #badge>
                                  {{ checkedCredentials.length }}
                                </template>
                              </v-badge>
                            </v-list-item-title>
                          </v-list-item>
                        </template>
                        {{ $t("sushi.mark_as_fixed.tooltip") }}
                      </v-tooltip>
                      <v-tooltip location="bottom" max-width="600px">
                        <template #activator="{ props }">
                          <v-list-item
                            :disabled="
                              checkedBrokenCredentials.length === 0 ||
                              moreActionsLoading
                            "
                            @click="triggerMarkFixed"
                            v-bind="props"
                          >
                            <v-list-item-title>
                              <v-icon
                                class="mr-2"
                                size="small"
                                color="lighterIcons"
                                >fa fa-tools</v-icon
                              >
                              {{ $t("sushi.mark_as_fixed.button") }}
                              <v-badge color="secondary" inline class="mt-1">
                                <template #badge>
                                  {{ checkedBrokenCredentials.length }}
                                </template>
                              </v-badge>
                            </v-list-item-title>
                          </v-list-item>
                        </template>
                        {{ $t("sushi.mark_as_fixed.tooltip") }}
                      </v-tooltip>
                      <v-tooltip location="bottom" max-width="600px">
                        <template #activator="{ props }">
                          <v-list-item
                            :disabled="
                              checkedWithManualReportTypes.length === 0 ||
                              moreActionsLoading
                            "
                            @click="triggerReportTypesFromPlatform"
                            v-bind="props"
                          >
                            <v-list-item-title>
                              <v-icon
                                class="mr-2"
                                size="small"
                                color="lighterIcons"
                                >fa fa-cogs</v-icon
                              >
                              {{ $t("sushi.report_type_from_platform.derive") }}
                              <v-badge color="secondary" inline class="mt-1">
                                <template #badge>
                                  {{ checkedWithManualReportTypes.length }}
                                </template>
                              </v-badge>
                            </v-list-item-title>
                          </v-list-item>
                        </template>
                        {{ $t("sushi.report_type_from_platform.tooltip") }}
                      </v-tooltip>
                      <v-tooltip location="bottom">
                        <template #activator="{ props }">
                          <v-list-item
                            :disabled="
                              checkedCredentials.length === 0 ||
                              moreActionsLoading
                            "
                            @click="$refs.exportSubmit.submit()"
                            v-bind="props"
                          >
                            <v-list-item-title>
                              <v-icon
                                class="mr-2"
                                size="small"
                                color="lighterIcons"
                                >fa fa-file-export</v-icon
                              >
                              {{ $t("export_selected") }}
                              <v-badge color="secondary" inline class="mt-1">
                                <template #badge>
                                  {{ checkedCredentials.length }}
                                </template>
                              </v-badge>
                            </v-list-item-title>
                            <form
                              :action="exportUrl"
                              method="post"
                              ref="exportSubmit"
                            >
                              <input
                                type="hidden"
                                name="csrfmiddlewaretoken"
                                style="display: none"
                                :value="getCSRFToken"
                              />
                              <div
                                v-for="checkedCredential in checkedCredentials"
                                :key="checkedCredential.pk"
                                style="display: none"
                              >
                                <input
                                  type="hidden"
                                  :id="checkedCredential.pk"
                                  name="pk"
                                  :value="checkedCredential.pk"
                                />
                              </div>
                            </form>
                          </v-list-item>
                        </template>
                        {{ $t("export_selected_tooltip") }}
                      </v-tooltip>
                      <v-tooltip location="bottom" max-width="600px">
                        <template #activator="{ props }">
                          <v-list-item
                            :disabled="
                              checkedCredentialsNotEnabled.length === 0 ||
                              moreActionsLoading
                            "
                            @click="updateEnabled(true)"
                            v-bind="props"
                          >
                            <v-list-item-title>
                              <v-icon
                                class="mr-2"
                                size="small"
                                color="lighterIcons"
                                >fa fa-play</v-icon
                              >
                              {{ $t("sushi.set_enabled") }}
                              <v-badge color="secondary" inline class="mt-1">
                                <template #badge>
                                  {{ checkedCredentialsNotEnabled.length }}
                                </template>
                              </v-badge>
                            </v-list-item-title>
                          </v-list-item>
                        </template>
                        {{ $t("sushi.set_enabled_tooltip") }}
                      </v-tooltip>
                      <v-tooltip location="bottom" max-width="600px">
                        <template #activator="{ props }">
                          <v-list-item
                            :disabled="
                              checkedCredentialsEnabled.length === 0 ||
                              moreActionsLoading
                            "
                            @click="updateEnabled(false)"
                            v-bind="props"
                          >
                            <v-list-item-title>
                              <v-icon
                                class="mr-2"
                                size="small"
                                color="lighterIcons"
                                >fa fa-ban</v-icon
                              >
                              {{ $t("sushi.unset_enabled") }}
                              <v-badge color="secondary" inline class="mt-1">
                                <template #badge>
                                  {{ checkedCredentialsEnabled.length }}
                                </template>
                              </v-badge>
                            </v-list-item-title>
                          </v-list-item>
                        </template>
                        {{ $t("sushi.unset_enabled_tooltip") }}
                      </v-tooltip>
                    </v-list>
                  </v-menu>
                </template>
                {{ $t("bulk_actions") }}
              </v-tooltip>
            </v-col>
          </v-row>

          <v-row>
            <v-col>
              <div class="caption">
                {{ $t("sushi.update.can_update_legend_header") }}
              </div>
              <div>
                <v-icon size="x-small" class="mr-1" color="info"
                  >far fa-arrow-alt-circle-up</v-icon
                >
                <span class="caption">{{
                  $t("sushi.update.can_update_legend")
                }}</span>
              </div>
              <div>
                <v-icon size="x-small" class="mr-1" color="info"
                  >fas fa-arrow-alt-circle-up</v-icon
                >
                <span class="caption">{{
                  $t("sushi.update.can_update_verified_legend")
                }}</span>
              </div>
              <div>
                <v-icon size="x-small" class="mr-1" color="error"
                  >far fa-arrow-alt-circle-left</v-icon
                >
                <span class="caption">{{
                  $t("sushi.update.cannot_update_broken_legend")
                }}</span>
              </div>
            </v-col>
          </v-row>

          <v-row>
            <v-col cols="3" md="2" xl="2">
              <v-select
                v-model="potentialIssuesFilter"
                :label="$t('potential_issues.label')"
                density="comfortable"
                class="mt_without_label"
                :items="[
                  {
                    title: $t('potential_issues.broken'),
                    value: 'broken',
                    tooltip: $t('potential_issues_tt.broken'),
                  },
                  {
                    title: $t('potential_issues.not_validated'),
                    value: 'not_validated',
                    tooltip: $t('potential_issues_tt.not_validated'),
                  },
                  {
                    title: $t('potential_issues.can_update_verified'),
                    value: 'can_update_verified',
                    tooltip: $t('potential_issues_tt.can_update_verified'),
                  },
                  {
                    title: $t('potential_issues.can_update'),
                    value: 'can_update',
                    tooltip: $t('potential_issues_tt.can_update'),
                  },
                  {
                    title: $t('potential_issues.duplicated'),
                    value: 'duplicated',
                    tooltip: $t('potential_issues_tt.duplicated'),
                  },
                ]"
                single-line
                hide-details
                clearable
                clear-icon="fa fa-times"
              >
                <template #item="{ props, item }">
                  <v-tooltip location="right">
                    <template #activator="{ props: TooltipProps }">
                      <v-list-item v-bind="{ ...TooltipProps, ...props }">
                      </v-list-item>
                    </template>
                    {{ item.raw.tooltip }}
                  </v-tooltip>
                </template>
              </v-select>
            </v-col>
            <v-spacer></v-spacer>
            <v-col :cols="!$vuetify.display.smAndDown ? 2 : 4" md="2" xl="2">
              <v-select
                density="comfortable"
                :items="[
                  {
                    title: $t('last_harvestable_month_filter.all'),
                    value: null,
                  },
                  {
                    title: $t('last_harvestable_month_filter.set'),
                    value: true,
                  },
                  {
                    title: $t('last_harvestable_month_filter.not_set'),
                    value: false,
                  },
                ]"
                v-model="withLastHarvestableMonthSet"
                :label="$t('title_fields.last_harvestable_month')"
                style="min-width: 80px"
              ></v-select>
            </v-col>
            <v-col :cols="!$vuetify.display.smAndDown ? 2 : 6" md="2" xl="2">
              <v-select
                style="min-width: 100px"
                :items="[
                  { title: $t('sushi.all_counter_versions'), value: null },
                  { title: '4', value: 4 },
                  { title: '5', value: 5 },
                  { title: '5.1', value: 51 },
                ]"
                density="comfortable"
                v-model="counterVersion"
                :label="$t('labels.counter_version')"
              ></v-select>
            </v-col>
            <v-col
              v-if="!fixedPlatformId"
              :style="$vuetify.display.xs ? 'ml-2' : ''"
              :cols="!$vuetify.display.smAndDown ? 2 : 5"
            >
              <PlatformSelector
                :platforms="platformsSorted"
                style="min-width: 100px"
                v-model="platformFilter"
                :label="$t('labels.platform')"
                density="comfortable"
                :loading="loading"
              />
            </v-col>
            <v-col :cols="!$vuetify.display.smAndDown ? 2 : 5">
              <v-text-field
                v-model="searchDebounced"
                append-inner-icon="fa fa-search"
                :label="$t('labels.search')"
                density="comfortable"
                single-line
                hide-details
                clearable
                clear-icon="fa fa-times"
              ></v-text-field>
            </v-col>
          </v-row>
        </v-container>
      </v-card-title>
      <v-skeleton-loader
        v-if="loading"
        type="table"
        class="mt-5"
      ></v-skeleton-loader>
      <v-data-table-server
        v-else
        v-model="checkedCredentials"
        :items-length="sushiCredentialsCount"
        item-key="pk"
        :items="sushiCredentialsList"
        :headers="headers"
        v-model:items-per-page="itemsPerPage"
        v-model:sort-by="orderBy"
        v-model:page="page"
        multi-sort
        show-select
        density="default"
        return-object
      >
        <template #item.counter_reports="{ item, index }">
          <v-lazy
            :transition="false"
            :model-value="index < immediateRenderCount"
          >
            <span>
              <v-chip
                v-for="(report, index) in item.counter_reports_long"
                :key="index"
                class="mr-1 px-2"
                :class="
                  item.use_counter_reports_from_platform
                    ? 'font-weight-regular'
                    : 'font-weight-bold'
                "
                :color="
                  report.broken || item.use_counter_reports_from_platform
                    ? '#444444'
                    : 'teal-darken-2'
                "
                variant="tonal"
                label
                size="small"
              >
                <SushiReportIndicator
                  :report="report"
                  :derived-from-platform="
                    item.use_counter_reports_from_platform
                  "
                ></SushiReportIndicator>
              </v-chip>
            </span>
          </v-lazy>
        </template>
        <template #item.counter_version="{ item, index }">
          <v-lazy
            :transition="false"
            :model-value="index < immediateRenderCount"
          >
            <v-tooltip location="bottom" v-if="item.can_update && !item.broken">
              <template v-slot:activator="{ props }">
                <span v-bind="props">
                  <strong>{{
                    counterVersionToStr(item.counter_version)
                  }}</strong>
                  <i
                    class="fa-arrow-alt-circle-up ml-1"
                    :class="
                      item.has_51_provider ? 'text-info fas' : 'text-info far'
                    "
                  ></i>
                </span>
              </template>
              {{
                item.has_51_provider
                  ? $t("sushi.update.can_update_verified_legend")
                  : $t("sushi.update.can_update_legend")
              }}
            </v-tooltip>

            <v-tooltip
              location="bottom"
              v-else-if="item.can_update && item.broken"
            >
              <template v-slot:activator="{ props }">
                <span v-bind="props">
                  <strong>{{
                    counterVersionToStr(item.counter_version)
                  }}</strong>
                  <i class="far fa-arrow-alt-circle-left ml-1 text-error"></i>
                </span>
              </template>
              {{ $t("sushi.update.cannot_update_broken_tt") }}
            </v-tooltip>

            <strong v-else>{{
              counterVersionToStr(item.counter_version)
            }}</strong>
          </v-lazy>
        </template>
        <template #item.last_harvestable_month="{ item, index }">
          <v-lazy
            :transition="false"
            :model-value="index < immediateRenderCount"
          >
            <span>
              <span v-if="item.last_harvestable_month">{{
                item.last_harvestable_month.slice(0, 7)
              }}</span>
            </span>
          </v-lazy>
        </template>
        <template #item.actions="{ item, index }">
          <v-lazy
            :transition="false"
            :model-value="index < immediateRenderCount"
          >
            <span>
              <v-btn
                v-if="!item.locked_for_me"
                variant="text"
                size="small"
                color="secondary"
                @click.stop="
                  selectedCredentials = item;
                  showEditDialog = true;
                "
              >
                <v-icon left size="x-small" class="mr-4">fas fa-edit</v-icon>
                {{ $t("actions.edit") }}
              </v-btn>
              <v-btn
                variant="text"
                size="small"
                color="secondary"
                @click.stop="
                  selectedCredentials = item;
                  showDetailsDialog = true;
                "
              >
                <v-icon left size="x-small" class="mr-4">fa fa-list</v-icon>
                {{ $t("actions.show_attempts") }}
              </v-btn>
              <v-tooltip location="left">
                <template v-slot:activator="{ props }">
                  <v-btn
                    v-bind="props"
                    variant="text"
                    size="small"
                    color="secondary"
                    @click.stop="
                      selectedCredentials = item;
                      showDataDialog = true;
                    "
                  >
                    <v-icon left size="x-small" class="mr-4"
                      >far fa-calendar-alt</v-icon
                    >
                    {{ $t("actions.show_overview") }}
                  </v-btn>
                </template>
                {{ $t("actions.show_overview_details") }}
              </v-tooltip>
            </span>
          </v-lazy>
        </template>
        <template #item.title="{ item, index }">
          <v-lazy
            :transition="false"
            :model-value="index < immediateRenderCount"
          >
            <span>
              <v-tooltip
                v-if="warnSameCredentials(item)"
                max-width="400"
                location="bottom"
              >
                <template v-slot:activator="{ props }">
                  <v-icon
                    color="warning"
                    class="pe-1"
                    size="small"
                    v-bind="props"
                    >fa fa-copy</v-icon
                  >
                  {{ item.title }}
                </template>
                {{ $t(warnSameCredentialsText(item)) }}
              </v-tooltip>
              <span v-else>
                {{ item.title }}
              </span>
            </span>
          </v-lazy>
        </template>
        <template #item.enabled="{ item, index }">
          <v-lazy
            :transition="false"
            :model-value="index < immediateRenderCount"
          >
            <span>
              <CheckMark
                true-color="error"
                false-color="error"
                v-if="item.broken"
                :model-value="item.enabled"
              ></CheckMark>
              <CheckMark
                true-color="warning"
                false-color="warning"
                v-else-if="!item.verified"
                :model-value="item.enabled"
              ></CheckMark>
              <CheckMark v-else :model-value="item.enabled"></CheckMark>
              <v-tooltip location="bottom" v-if="item.broken" max-width="400">
                <template v-slot:activator="{ props }">
                  <v-icon class="ml-1" size="small" color="error" v-bind="props"
                    >fa fa-exclamation-triangle</v-icon
                  >
                </template>
                {{ $t("is_broken") }}
              </v-tooltip>
              <v-tooltip
                location="bottom"
                v-else-if="!item.verified"
                max-width="400"
              >
                <template v-slot:activator="{ props }">
                  <v-icon
                    size="small"
                    class="ml-1"
                    color="warning"
                    v-bind="props"
                    >fa fa-exclamation-triangle</v-icon
                  >
                </template>
                {{ $t("unverified_tooltip") }}
              </v-tooltip>
            </span>
          </v-lazy>
        </template>
        <template #item.outside_consortium="{ item, index }">
          <v-lazy
            :transition="false"
            :model-value="index < immediateRenderCount"
          >
            <span>
              <CheckMark :model-value="item.outside_consortium"></CheckMark>
            </span>
          </v-lazy>
        </template>
        <template #item.lock_level="{ item, index }">
          <v-lazy
            :transition="false"
            :model-value="index < immediateRenderCount"
          >
            <span>
              <!-- locked for me -->
              <v-tooltip
                location="bottom"
                v-if="item.locked && item.locked_for_me"
              >
                <template v-slot:activator="{ props }">
                  <v-icon size="small" v-bind="props" color="red"
                    >fa fa-fw fa-lock</v-icon
                  >
                </template>
                {{ $t("is_locked") }} {{ $t("cannot_edit") }}
              </v-tooltip>
              <!-- locked, but I can edit -->
              <v-tooltip location="bottom" v-else-if="item.locked">
                <template v-slot:activator="{ props }">
                  <v-icon size="small" v-bind="props" color="red"
                    >fa fa-fw fa-lock</v-icon
                  >
                </template>
                {{ $t("is_locked") }} {{ $t("can_edit") }}
              </v-tooltip>
              <!-- not locked at all -->
              <v-tooltip location="bottom" v-else>
                <template v-slot:activator="{ props }">
                  <v-icon size="small" v-bind="props" color="green"
                    >fa fa-fw fa-lock-open</v-icon
                  >
                </template>
                {{ $t("is_unlocked") }}
              </v-tooltip>
              <v-tooltip location="bottom" v-if="item.can_lock">
                <template v-slot:activator="{ props }">
                  <v-btn
                    variant="text"
                    icon
                    @click="toggleLock(item)"
                    v-bind="props"
                    ><v-icon size="small" color="#0000008a"
                      >fas fa-key</v-icon
                    ></v-btn
                  >
                </template>
                {{ $t("can_lock") }}
              </v-tooltip>
            </span>
          </v-lazy>
        </template>
        <template #item.organization__name="{ item, index }">
          <v-lazy
            :transition="false"
            :model-value="index < immediateRenderCount"
          >
            <span>
              <span>{{ item.organization.name }}</span>
              <v-tooltip location="bottom" v-if="item.last_updated_by">
                <template v-slot:activator="{ props }">
                  <span v-bind="props">
                    <i class="text-grey-lighten-1 fas fa-user ml-1"></i>
                  </span>
                </template>
                {{
                  $t("last_updated_tooltip", {
                    time: isoDateTimeFormat(item.last_updated),
                    user: userToString(item.last_updated_by, "-", true),
                  })
                }}
              </v-tooltip>
            </span>
          </v-lazy>
        </template>
        <template #header.data-table-select>
          <SelectAllCheckbox
            :selected-count="checkedCredentials.length"
            :selected-on-page-count="checkedCredentialsOnPage.length"
            :total-count="sushiCredentialsCount"
            :on-page-count="sushiCredentialsList.length"
            @deselect="checkedCredentials = []"
            @select-all-on-page="selectAllOnPage"
            @select-all="selectAllCredentials"
          ></SelectAllCheckbox>
        </template>
      </v-data-table-server>
    </v-card>
    <v-dialog
      v-model="showEditDialog"
      v-if="showEditDialog"
      :max-width="dialogMaxWidth"
    >
      <SushiCredentialsEditDialog
        :credentials-object="selectedCredentials"
        v-model="showEditDialog"
        @update-credentials="updateCredentials"
        @deleted="deleteCredentials"
        key="edit"
        @close-dialog="showEditDialog = false"
      ></SushiCredentialsEditDialog>
    </v-dialog>
    <v-dialog
      v-model="showCreateDialog"
      v-if="showCreateDialog"
      :max-width="dialogMaxWidth"
    >
      <SushiCredentialsEditDialog
        v-model="showCreateDialog"
        @close-dialog="showCreateDialog = false"
        @update-credentials="updateCredentials"
        @deleted="deleteCredentials"
        key="create"
        :fixed-platform="fixedPlatformId"
      ></SushiCredentialsEditDialog>
    </v-dialog>
    <v-dialog v-model="showDetailsDialog">
      <SushiAttemptListWidget
        v-if="selectedCredentials"
        :credentials="selectedCredentials"
        @close="closeDetailsDialog"
      >
      </SushiAttemptListWidget>
    </v-dialog>
    <v-dialog
      v-model="showTestDialog"
      max-width="1320px"
      content-class="top-dialog"
      max-height="80vh"
    >
      <v-card class="pb-5">
        <v-card-title>{{ $t("test_dialog") }}</v-card-title>
        <v-card-text class="pb-0">
          <HarvestSelectedWidget
            v-if="showTestDialog"
            :credentials="checkedCredentials"
            ref="testWidget"
            :retry-interval="5000"
            :show-platform="true"
            :show-organization="true"
          >
          </HarvestSelectedWidget>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn
            @click="stopTestDialog()"
            variant="elevated"
            color="defaultButton"
            class="mr-5"
            >{{ $t("close") }}</v-btn
          >
        </v-card-actions>
      </v-card>
    </v-dialog>
    <v-dialog
      v-model="showDataDialog"
      v-if="showDataDialog"
      :max-width="dialogMaxWidth"
    >
      <SushiCredentialsDataDialog
        :credentials="selectedCredentials"
        @close="closeDataDialog"
        @reload-credentials="loadSushiCredentialsList"
      ></SushiCredentialsDataDialog>
    </v-dialog>
    <v-dialog
      v-model="showLastHarvestableMonthDialog"
      v-if="showLastHarvestableMonthDialog"
      max-width="600px"
    >
      <LastHarvestableMonthWidget
        :credentials="checkedCredentials"
        @close="showLastHarvestableMonthDialog = false"
        @apply="applyLastHarvestableMonthDialog"
        update-backend
      ></LastHarvestableMonthWidget>
    </v-dialog>

    <v-dialog
      v-model="showMarkAsFixedDialog"
      v-if="showMarkAsFixedDialog"
      max-width="600px"
    >
      <MarkCredentialsAsFixedWidget
        :credentials="checkedBrokenCredentials"
        @close="closeMarkAsFixedDialog"
        @update-credentials="updateCredentials"
      ></MarkCredentialsAsFixedWidget>
    </v-dialog>

    <v-dialog
      v-model="showCloneToNewerDialog"
      v-if="showCloneToNewerDialog"
      max-width="800px"
    >
      <CloneCredentialsToNewerWidget
        :credentials="checkedUpdatableCredentials"
        @close="closeCloneToNewer"
        @new-credentials="credentialsClonedHandler"
      ></CloneCredentialsToNewerWidget>
    </v-dialog>
  </v-container>
</template>

<script>
import PlatformSelector from "@/components/selectors/PlatformSelector.vue";
import CloneCredentialsToNewerWidget from "@/components/sushi/CloneCredentialsToNewerWidget";
import HarvestSelectedWidget from "@/components/sushi/HarvestSelectedWidget";
import LastHarvestableMonthWidget from "@/components/sushi/LastHarvestableMonthWidget";
import MarkCredentialsAsFixedWidget from "@/components/sushi/MarkCredentialsAsFixedWidget";
import SushiAttemptListWidget from "@/components/sushi/SushiAttemptListWidget";
import SushiCredentialsDataDialog from "@/components/sushi/SushiCredentialsDataDialog";
import SushiCredentialsEditDialog from "@/components/sushi/SushiCredentialsEditDialog";
import SushiReportIndicator from "@/components/sushi/SushiReportIndicator";
import SelectAllCheckbox from "@/components/tables/SelectAllCheckbox";
import CheckMark from "@/components/util/CheckMark";
import { isoDateTimeFormat } from "@/libs/dates";
import { counterVersionToStr } from "@/libs/sushi";
import { userToString } from "@/libs/user";
import stateTracking from "@/mixins/stateTracking";
import axios from "axios";
import Cookies from "js-cookie";
import debounce from "lodash/debounce";
import { mapActions, mapGetters } from "vuex";

export default {
  name: "SushiCredentialsManagementWidget",

  components: {
    CheckMark,
    HarvestSelectedWidget,
    PlatformSelector,
    CloneCredentialsToNewerWidget,
    MarkCredentialsAsFixedWidget,
    LastHarvestableMonthWidget,
    SushiAttemptListWidget,
    SushiCredentialsEditDialog,
    SushiCredentialsDataDialog,
    SushiReportIndicator,
    SelectAllCheckbox,
  },
  mixins: [stateTracking],

  props: {
    dialogMaxWidth: {
      required: false,
      default: "1200px",
    },
    organizationId: {
      default: -1,
      type: Number,
      required: true,
    },
    fixedPlatformId: {
      default: null,
      type: Number,
      required: false,
    },
    potentialIssues: {
      default: null,
      type: String,
    },
  },

  data() {
    return {
      selectAllLoading: false,
      sushiCredentialsList: [],
      sushiCredentialsCount: 0,
      platforms: [],
      search: "",
      selectedCredentials: null,
      immediateRenderCount: 12,
      showEditDialog: false,
      showDetailsDialog: false,
      showCreateDialog: false,
      showDataDialog: false,
      showLastHarvestableMonthDialog: false,
      showMarkAsFixedDialog: false,
      showCloneToNewerDialog: false,
      loading: false,
      counterVersion: null,
      withLastHarvestableMonthSet: null,
      checkedCredentials: [],
      showTestDialog: false,
      potentialIssuesFilter: this.potentialIssues,
      platformFilter: null,
      moreActionsLoading: false,
      // table options
      page: 1,
      itemsPerPage: 25,
      orderBy: [
        { key: "organization__name", order: "asc" },
        { key: "platform__name", order: "asc" },
        { key: "counter_version", order: "desc" },
      ],
      // state tracking support
      watchedAttrs: [
        {
          name: "potentialIssuesFilter",
          type: Boolean,
        },
        {
          name: "search",
          type: String,
          var: "sushi_search",
        },
        {
          name: "counterVersion",
          type: Number,
        },
        {
          name: "withLastHarvestableMonthSet",
          type: Boolean,
        },
        {
          name: "page",
          type: Number,
        },
        {
          name: "itemsPerPage",
          type: Number,
          var: "ipp",
        },
        {
          name: "orderBy",
          type: Object,
          alwaysTrack: true,
        },
        // {
        //   name: "orderDesc",
        //   type: Array,
        // },
        {
          name: "platformFilter",
          type: Number,
        },
        {
          name: "potentialIssuesFilter",
          type: String,
        },
      ],
    };
  },
  computed: {
    ...mapGetters({
      consortialInstall: "consortialInstall",
      contactEmail: "contactEmail",
      subjectForImportCredEmail: "subjectForImportCredEmail",
    }),
    getCSRFToken() {
      let csrftoken = Cookies.get("csrftoken");
      return csrftoken;
    },
    headers() {
      const large = this.$vuetify.display.lgAndUp;
      let allHeaders = [
        {
          title: this.$i18n.t("title"),
          value: "title",
          class: "wrap",
          key: "title",
        },
        {
          title: this.$i18n.t("organization"),
          value: "organization.name",
          class: "wrap",
          key: "organization__name",
        },
        {
          title: this.$i18n.t("platform"),
          value: "platform.name",
          key: "platform__name",
        },
        {
          title: this.$i18n.t("title_fields.counter_version"),
          value: "counter_version",
          align: "center",
          key: "counter_version",
        },
        {
          title: this.$i18n.t("title_fields.active_reports"),
          value: "counter_reports",
          sortable: false,
        },
        {
          title: this.$i18n.t("title_fields.last_harvestable_month"),
          value: "last_harvestable_month",
          sortable: false,
        },
        {
          title: this.$i18n.t("title_fields.outside_consortium"),
          value: "outside_consortium",
          show: this.consortialInstall && large,
          key: "outside_consortium",
        },
        {
          title: this.$i18n.t("sushi.enabled"),
          value: "enabled",
          key: "enabled",
        },
        {
          title: this.$i18n.t("title_fields.lock"),
          value: "locked",
          show: this.consortialInstall && large,
          key: "lock_level",
        },
        {
          title: this.$i18n.t("title_fields.actions"),
          value: "actions",
          sortable: false,
        },
      ];
      return allHeaders.filter(
        (row) => !row.hasOwnProperty("show") || row.show,
      );
    },
    searchDebounced: {
      get() {
        return this.search;
      },
      set: debounce(function (value) {
        this.search = value;
      }, 500),
    },
    dataUrl() {
      return "/api/sushi-credentials/";
    },
    exportUrl() {
      let base = `/api/sushi-credentials/export-credentials/?organization=${this.organizationId}`;
      if (this.fixedPlatformId) {
        base += `&platform=${this.fixedPlatformId}`;
      }
      return base;
    },
    exportForImportUrl() {
      let base = `/api/sushi-credentials/import-template/?organization=${this.organizationId}`;
      if (this.fixedPlatformId) {
        base += `&platform=${this.fixedPlatformId}`;
      }
      return base;
    },
    platformsSorted() {
      return this.platforms.toSorted((a, b) => a.name.localeCompare(b.name));
    },
    platformMap() {
      return new Map(this.platforms.map((p) => [p.pk, p]));
    },
    checkedBrokenCredentials() {
      return this.checkedCredentials.filter((e) => e.any_broken);
    },
    checkedUpdatableCredentials() {
      return this.checkedCredentials.filter((e) => e.can_update && !e.broken);
    },
    checkedWithManualReportTypes() {
      return this.checkedCredentials.filter(
        (e) => !e.use_counter_reports_from_platform,
      );
    },
    credentialsListUrlFilters() {
      let params = {
        page_size: this.itemsPerPage,
      };
      if (this.searchDebounced) {
        params.search = this.searchDebounced;
      }
      if (this.currentPlatformFilter) {
        params.platform = this.currentPlatformFilter;
      }
      if (this.organizationId) {
        params.organization = this.organizationId;
      }
      if (this.potentialIssuesFilter) {
        params.potential_issues = this.potentialIssuesFilter;
      }
      if (this.withLastHarvestableMonthSet != null) {
        params.last_harvestable_month = this.withLastHarvestableMonthSet;
      }
      if (this.counterVersion) {
        params.counter_version = this.counterVersion;
      }
      if (this.orderingFilter) {
        params.ordering = this.orderingFilter;
      }
      return new URLSearchParams(params);
    },
    currentPlatformFilter() {
      // If platform is fixed always use the filter
      return this.fixedPlatformId || this.platformFilter;
    },
    orderingFilter() {
      return this.orderBy
        .map((e) => `${e.order == "desc" ? "-" : ""}${e.key}`)
        .join(",");
    },
    checkedCredentialsOnPage() {
      const checkedCredentialsIds = this.checkedCredentials.map((e) => e.pk);
      return this.sushiCredentialsList.filter((e) =>
        checkedCredentialsIds.includes(e.pk),
      );
    },
    checkedCredentialsEnabled() {
      return this.checkedCredentials.filter((e) => e.enabled);
    },
    checkedCredentialsNotEnabled() {
      return this.checkedCredentials.filter((e) => !e.enabled);
    },
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
      loadSushiCredentialsCount: "loadSushiCredentialsCount",
      getPageSetting: "getPageSetting",
      setPageSetting: "setPageSetting",
    }),
    counterVersionToStr(value) {
      return counterVersionToStr(value);
    },
    userToString,
    isoDateTimeFormat,
    downloadImportTemplate() {
      const link = document.createElement("a");
      link.href = this.exportForImportUrl;
      document.body.appendChild(link);
      link.click();
    },
    async showImportCredentialsModal() {
      const res = await this.$confirm(
        this.$t("import_credentials_confirm_text_1") +
          "<br><br>" +
          this.$t("import_credentials_confirm_text_2") +
          ` <a href="mailto:${this.contactEmail}?subject=${this.subjectForImportCredEmail}">${this.contactEmail}</a> ` +
          this.$t("import_credentials_confirm_text_3") +
          ` "${this.subjectForImportCredEmail}". ` +
          this.$t("import_credentials_confirm_text_4"),
        {
          title: this.$t("import_credentials_confirm_title"),
          buttonTrueText: this.$t("download_file"),
          buttonFalseText: this.$t("close"),
          color: "primary",
          icon: "fa fa-info-circle",
          width: 500,
        },
      );
      if (res) {
        this.downloadImportTemplate();
      }
    },
    async loadSushiCredentialsList() {
      this.loading = true;
      try {
        let response = await axios.get(
          `${this.dataUrl}?${this.credentialsListUrlFilters.toString()}&page=${
            this.page
          }`,
        );
        this.sushiCredentialsList = response.data.results;
        this.sushiCredentialsCount = response.data.count;
        this.platforms = response.data.platforms;
        this.sushiCredentialsList.forEach((item) =>
          this.preprocessCredentials(item),
        );
      } catch (error) {
        this.showSnackbar({
          content: "Error loading credentials list: " + error,
        });
      } finally {
        this.loading = false;
      }
    },
    updateCredentials(credentials) {
      if (
        this.selectedCredentials &&
        (this.selectedCredentials.same_global !== credentials.same_global ||
          this.selectedCredentials.same_in_org !== credentials.same_in_org)
      ) {
        // Same credentials were updated => refetch all credentials to update
        // the states of other credentials
        this.loadSushiCredentialsList();
        return;
      }
      this.preprocessCredentials(credentials);
      // the new credentials as returned by the edit dialog
      // we put them at the right place in the list of credentials
      let found = this.sushiCredentialsList
        .map((e) => e.pk)
        .includes(credentials.pk);

      // Uncheck credentials when an action over a single credentials was performed
      this.checkedCredentials = [];

      this.sushiCredentialsList = this.sushiCredentialsList.map((e) =>
        e.pk == credentials.pk ? credentials : e,
      );

      if (!found) {
        this.loadSushiCredentialsList();
      }
      // update the model used by the edit dialog
      if (this.selectedCredentials) {
        this.selectedCredentials = credentials;
      }
    },
    deleteCredentials() {
      this.loadSushiCredentialsList();
    },
    preprocessCredentials(item) {
      if (typeof item.platform === "number") {
        // Convert platfrom id to platform object
        item.platform = this.platformMap.get(item.platform);
      }

      if (!item.platform.name) {
        // use platform short_name instead of name if name is empty
        item.platform.name = item.platform.short_name;
      }
    },
    async toggleLock(credentials) {
      let newLockLevel = 400;
      if (credentials.locked) {
        newLockLevel = 300;
      }
      try {
        let response = await axios.post(
          `/api/sushi-credentials/${credentials.pk}/lock/`,
          { lock_level: newLockLevel },
        );
        credentials.lock_level = response.data.lock_level;
        credentials.locked = response.data.locked;
      } catch (error) {
        this.showSnackbar({
          content: "Error (un)locking credentials: " + error,
          color: "error",
        });
      }
    },
    closeDetailsDialog() {
      this.selectedCredentials = null;
      this.showDetailsDialog = false;
    },
    closeDataDialog() {
      this.selectedCredentials = null;
      this.showDataDialog = false;
    },
    applyLastHarvestableMonthDialog({ updated }) {
      if (updated > 0) {
        this.loadSushiCredentialsList();
        this.checkedCredentials = [];
      }
      this.showLastHarvestableMonthDialog = false;
    },
    closeMarkAsFixedDialog() {
      this.showMarkAsFixedDialog = false;
    },
    closeCloneToNewer(refresh) {
      if (refresh) {
        this.loadSushiCredentialsList();
        this.checkedCredentials = [];
      }
      this.showCloneToNewerDialog = false;
    },
    activateCreateDialog() {
      this.showCreateDialog = true;
    },
    testChecked(dialogFlag) {
      if (this.checkedCredentials.length > 0) {
        this[dialogFlag] = true;
      } else {
        this.$confirm(this.$t("select_at_least_one_credentials"), {
          title: this.$t("no_credentials_selected"),
          buttonTrueText: this.$t("close"),
          buttonFalseText: null,
          color: "warning",
          icon: "fa fa-warning",
        });
      }
    },
    triggerMarkFixed() {
      if (this.checkedBrokenCredentials.length > 0) {
        this.showMarkAsFixedDialog = true;
      } else {
        this.$confirm(this.$t("select_at_least_one_broken_credentials"), {
          title: this.$t("no_broken_credentials_selected"),
          buttonTrueText: this.$t("close"),
          buttonFalseText: null,
          width: 600,
          color: "warning",
          icon: "fa fa-warning",
          buttonTrueVariant: "elevated",
        });
      }
    },
    async triggerReportTypesFromPlatform() {
      if (this.checkedWithManualReportTypes.length > 0) {
        this.moreActionsLoading = true;
        try {
          let response = await axios.post(
            "/api/sushi-credentials/switch-to-platforms-report-types/",
            this.checkedWithManualReportTypes.map((e) => {
              return {
                credentials_id: e.pk,
              };
            }),
          );
          if (response.data.updated > 0) {
            this.showSnackbar({
              content: this.$t("report_types_derived_from_platform_set"),
              color: "success",
            });
            this.loadSushiCredentialsList();
            this.checkedCredentials = [];
          }
        } catch (error) {
          this.showSnackbar({
            content:
              "Could not switch credentials to use counter reports from platform: " +
              error,
            color: "error",
          });
        } finally {
          this.moreActionsLoading = false;
        }
      }
    },
    async updateEnabled(enabled) {
      const credentials = enabled
        ? this.checkedCredentialsNotEnabled
        : this.checkedCredentialsEnabled;
      const credentials_ids = credentials.map((e) => e.pk);
      if (credentials_ids.length == 0) {
        return;
      }

      this.moreActionsLoading = true;
      try {
        let response = await axios.post(
          "/api/sushi-credentials/update-enabled/",
          {
            enabled: enabled,
            credentials: credentials_ids,
          },
        );
        if (response.data.updated > 0) {
          this.showSnackbar({
            content: enabled
              ? this.$t("sushi.set_enabled_success")
              : this.$t("sushi.unset_enabled_success"),
            color: "success",
          });
          this.loadSushiCredentialsList();
          this.checkedCredentials = [];
        }
      } catch (error) {
        this.showSnackbar({
          content: "Could not update credentials: " + error,
          color: "error",
        });
      } finally {
        this.moreActionsLoading = false;
      }
    },
    triggerCloneToNewer() {
      if (this.checkedUpdatableCredentials.length > 0) {
        this.showCloneToNewerDialog = true;
      } else {
        this.$confirm(this.$t("select_at_least_one_clonable_credentials"), {
          title: this.$t("no_clonable_credentials_selected"),
          buttonTrueText: this.$t("close"),
          buttonFalseText: null,
          width: 600,
          color: "warning",
          icon: "fa fa-warning",
        });
      }
    },
    stopTestDialog() {
      if (this.$refs.testWidget) {
        this.$refs.testWidget.clean();
      }
      this.showTestDialog = false;
      this.loadSushiCredentialsList();
      this.loadSushiCredentialsCount();
    },
    warnSameCredentials(creds) {
      if (this.consortialInstall) {
        return creds.same_global > 1;
      } else {
        return creds.same_in_org > 1;
      }
    },
    warnSameCredentialsText(creds) {
      if (creds.same_in_org > 1) {
        return "warn_same_credentials_in_org_tooltip";
      }
      if (creds.same_global > 1) {
        return "warn_same_credentials_global_tooltip";
      }
      return "";
    },
    async credentialsClonedHandler() {
      await this.loadSushiCredentialsList();
      this.checkedCredentials = [];
    },
    selectAllOnPage() {
      this.checkedCredentials = [...this.sushiCredentialsList];
    },
    async selectAllCredentials() {
      this.selectAllLoading = true;
      try {
        let response = await axios.get(
          `${this.dataUrl}?${this.credentialsListUrlFilters.toString()}`,
        );
        let downloaded = response.data.results;
        downloaded.forEach((cred) => {
          cred.platform = this.platformMap.get(cred.platform);
        });
        let downloadedMap = new Map(downloaded.map((e) => [e.pk, e]));

        this.checkedCredentials = downloaded;
        // Update current list objects
        this.sushiCredentialsList = this.sushiCredentialsList.map((e) =>
          downloadedMap.get(e.pk),
        );
      } catch (error) {
        this.showSnackbar({
          content: "Error loading credentials to select: " + error,
        });
      } finally {
        this.selectAllLoading = false;
      }
    },
  },

  watch: {
    credentialsListUrlFilters() {
      this.page = 1;
      this.checkedCredentials = [];
      this.loadSushiCredentialsList();
    },
    showEditDialog(value) {
      if (!value) {
        this.selectedCredentials = null;
        this.loadSushiCredentialsCount();
      }
    },
    showCreateDialog(value) {
      if (!value) {
        this.selectedCredentials = null;
        this.loadSushiCredentialsCount();
      }
    },
    dataUrl() {
      this.loadSushiCredentialsList();
    },
    page() {
      this.loadSushiCredentialsList();
    },
    itemsPerPage() {
      this.setPageSetting({
        page: this.$route.name,
        key: "itemsPerPage",
        value: this.itemsPerPage,
      });
    },
  },
  async mounted() {
    const ippSetting = await this.getPageSetting({
      page: this.$route.name,
      key: "itemsPerPage",
    });
    if (ippSetting) {
      this.itemsPerPage = ippSetting;
    }
    await this.loadSushiCredentialsList();
  },
};
</script>

<style lang="scss">
.v-selection-control--dirty .v-selection-control__input > .v-icon {
  color: rgba(0, 0, 0, 0.54);
}

.mt_without_label {
  margin-top: 3px;
}
</style>
