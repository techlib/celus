<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<i18n lang="yaml" src="@/locales/dialog.yaml"></i18n>

<i18n lang="yaml" src="@/locales/sources.yaml"></i18n>

<i18n lang="yaml" src="@/locales/sushi.yaml"></i18n>

<i18n lang="yaml">
en:
  add_custom_param: Add custom parameter
  add_custom_param_tooltip: Use this to add parameters for which there is no specific field elsewhere.
  test_dialog: Harvest data to verify credentials
  all_versions_used: All versions already defined for this organization and platform - to make changes, edit the corresponding record
  ignore_and_save: Ignore and save
  outside: Purchased outside of consortium
  outside_tooltip: Marks if access to this resource was purchased outside the consortium.
  only_managers_can_change: Only managers may change this option.
  title:
    edit_sushi_credentials: Edit SUSHI credentials
  delete_success: Sushi credentials were successfully removed
  title_label: Title
  title_tooltip: You can give the credentials a descriptive title for easier identification. A title is required when you have more than one set of credentials for the same SUSHI server.
  credentials_conflict_hint: Credentials for this organization, platform and COUNTER version already exist.
  extra_attributes: Extra attributes - fill only if instructed by provider
  extra_attributes_tooltip: The following section is used for attributes which are only used by some providers. If the credentials given to you by the provider contain fields that do not correspond to any of the fields above, you can fill them in here.
  platform_filter_tooltip: This field is used only by some providers. If the credentials given to you by the provider contain filter "platform", you can fill it in here.
  really_delete: Do you really want to delete these credentials? (Downloaded data will be preserved)
  broken: These credentials were marked as broken. Harvesting will be disabled until the credentials are changed.
  broken_unbreak_manually:
    If you think that the credentials should not be marked as broken anymore (for example because there
    were connection issues that have been resolved in the meantime), you can manually mark them as fixed.
  mark_fixed: Mark fixed
  mark_fixed_success: Credentials were marked as fixed
  broken_reports_warning: |
    Some active reports have been marked as broken by CELUS - they are probably not supported by this platform.
    Either deactivate them or, if you are sure they are supported, you can use the button below to mark them as fixed.
    Note that if the report is not supported, it will break again during the next harvest.
  url_hint_no_report: "URL should not contain the '/reports/' part and anything beyond this. For example 'https://example.com/sushi5/reports/tr?customer_id=1' should be cropped to 'https://example.com/sushi5/'"
  url_hint_no_query: "URL should not contain any query parameters, i. e. there should be no '{search}' part"
  invalid_url: Please enter a valid URL
  url_must_use_https: URL must use HTTPS protocol in order to keep your credentials safe
  duplicate: Name must be unique
  active_report_types: Active report types
  error_saving: It was not possible to save the credentials. Please review the entered values.
  unverified_title: Credentials are not verified
  unverified_details: There are no successful harvests using the current version of these credentials.
  unverified_note: Please verify the credentials by performing a harvest. Note that the credentials won't be used for automatic harvesting unless a successful harvest is performed.
  same_credentials_title: Same credentials are already used
  same_credentials_global_text: The same credentials are already used by other organization. @:same_credentials_text
  same_credentials_in_org_text: The same credentials are already used for a different platform for this organization. @:same_credentials_text
  same_credentials_text: This indicates that one of these credentials is likely misconfigured and will lead to duplicate data being harvested.
  plan_harvest: Plan harvest
  requestor_id_not_required: Requestor ID is not required for this platform
  see_registry_hint: The Registry icon contains tooltip about this field from the COUNTER registry
  ip_authorization_required: According to the COUNTER registry, this platform requires IP authorization. In case you have problems with harvesting, please contact the platform provider with a request to add the following to the list of authorized IPs
  registry_platform_required: According to the COUNTER registry, this platform requires this attribute to be set
  registry_link: Link to the COUNTER registry record for the selected platform
  check_input: Please check the input, some fields do not have valid values
  cannot_edit_duplicated: These credentials conflict with another set of credentials (they have the same organization, platform and COUNTER version). Unless you delete one of the sets, you cannot edit any of them.
  cannot_create_duplicated: CELUS does not support multiple sets of credentials for the same organization, platform and COUNTER version.
  multiple_credentials_info_link: To get more information about duplicated credentials, please see {link}.
  this_article: this article
  show_debug: Show debugging information
  sushi_debug_links: SUSHI debugging links
  no_report_selected: No report selected
  last_harvestable_month: Last harvestable month
  last_harvestable_month_tt: |
    If you know that data is not available before a certain date, you can set this date here. CELUS will use this information
    and not try to harvest data before this date.
  last_harvestable_month_tt_disabled: To select the last harvestable month, please choose at least one report type.
  auto_update_url_text_off: Set URL manually
  auto_update_url_text_on: URL will be set automatically based on platform metadata
  auto_update_url_hint: URL is automatically managed by CELUS based on the platform metadata
  counter_report_from_platform_text_off: Set Report Types manually
  counter_report_from_platform_text_on: Report Types will be set automatically based on platform metadata
  counter_report_from_platform_hint: Report Types are automatically managed by CELUS based on the platform metadata
  counter_report_from_empty_platform_hint: The platform does not define any reports for the selected COUNTER version. Set them manually.
  edit_platform_tooltip: Edit platform

cs:
  add_custom_param: Přidat vlastní parametr
  add_custom_param_tooltip: Použijte toto tlačítko pro data, pro která nenajdete odpovídající políčko jinde.
  test_dialog: Stáhnout data pro ověření přihlašovacích údajů
  all_versions_used: Pro tuto platformu a organizaci jsou již všechny verze použity - pro změnu editujte příslušný záznam
  ignore_and_save: Ignoruj a ulož
  outside: Nákup mimo konzorcium
  outside_tooltip: Označuje přístupové údaje k nákupům mimo konzorcium.
  only_managers_can_change: Jen správci mohou měnit tuto hodnotu.
  title:
    edit_sushi_credentials: Přihlašovací údaje SUSHI
  delete_success: Přihlašovací údaje byly úspěšně odstraněny
  title_label: Název
  title_tooltip: Přihlašovacím údajům můžete přiřadit název pro lepší identifikaci. Název je také vyžadován v případě, že máte více než jednu sadu přihlašovacích údajů pro stejný SUSHI server.
  credentials_conflict_hint: Přihlašovací údaje pro tuto organizaci, platformu a verzi COUNTER již existují.
  extra_attributes: Extra atributy - vyplňte pouze pokud to poskytovatel vyžaduje
  extra_attributes_tooltip: Tato sekce je určena pro parametry, které jsou používány pouze některými poskytovateli. Pokud přihlašovací údaje, které jste obdrželi od poskytovatele obsahují údaje, pro které není ve formuláři výše položka, můžete je vyplnit zde.
  platform_filter_tooltip: Toto pole je používáno jen některými poskytovateli. Pokud přihlašovací údaje, které jste obdrželi, obsahují filtr "platform", můžete jej vyplnit zde.
  really_delete: Chcete opravdu smazat tyto přihlašovací údaje? (Stažená data budou zachována)
  broken: Tyto přihlašovací údaje byly označené jako nefunkční. Stahování bude vypnuto dokud nebudou údaje upraveny.
  broken_unbreak_manually:
    Pokud se domníváte, že by údaje neměly být označeny jako nefunkční (např. protože byl vyřešen problém s konektivitou
    který mohl způsobit jejich označení), můžete je ručně označit jako opravené.
  mark_fixed: Označit jako opravené
  mark_fixed_success: Přihlašovací údaje byly označeny jako opravené
  broken_reports_warning: |
    Některé aktivní reporty CELUS označil jako nefunkční - pravděpodobně nejsou na této platformě podporováné.
    Můžete je buď odstranit nebo případně, pokud jste si jisti že jsou podporovány, můžete je označit jako opravené.
    Pokud report není podporován, bude označen jako nefunkční během příštího stahování.
  url_hint_no_report: "URL by neměla obsahovat část s '/reports/' a cokoliv po ní. Např. 'https://example.com/sushi5/reports/tr?customer_id=1' by mělo být zkráceno na 'https://example.com/sushi5/'"
  url_hint_no_query: "URL nesmí obsahovat query parametry, tedy část '{search}'"
  invalid_url: Prosím zadejte platné URL
  url_must_use_https: URL musí používat HTTPS protokol pro zachování bezpečnosti vašich přihlašovacích údajů
  duplicate: Název musí být unikátní
  active_report_types: Aktivní typy reportů
  error_saving: Přihlašovací údaje nebylo možné uložit. Zkontrolujte prosím zadané hodnoty.
  unverified_title: Přihlašovací údaje nejsou ověřeny
  unverified_details: Současná verze těcho přihlašovacích údajů zatím nebyla úspěšně použita pro stažení dat.
  unverified_note: Ověřte prosím platnost přihlašovacích údajů stažením dat. Upozorňujeme, že dokud nebdou přihlašovací údaje ověřeny, nebude u nich probíhat automatické stahování dat.
  same_credentials_title: Stejné přístupové údaje jsou již použity jinde
  same_credentials_in_org_text: Stejné přístupové údaje jsou již použity pro jinou platformu u této organizace. @:same_credentials_text
  same_credentials_global_text: Stejné přístupové údaje jsou již použity jinou organizací. @:same_credentials_text
  same_credentials_text: To indikuje, že jedny z těchto přístupových údajů nejsou správně. Důsledkem bude zdvojení dat.
  plan_harvest: Naplánovat stahování
  requestor_id_not_required: Requestor ID není pro tuto platformu vyžadováno
  see_registry_hint: Ikona registru obsahuje nápovědu pro toto pole z COUNTER registru
  ip_authorization_required: Podle informací z COUNTER registru je pro tuto platformu vyžadována autorizace IP adresy. Pokud narazíte na problémy se sklízením dat, kontaktujte prosím poskytovatele a požádejte o povolení přístupu z následujících adres
  registry_platform_required: Podle informací z COUNTER registru je tato hodnota vyžadována
  registry_link: Odkaz do COUNTER registru pro vybranou platformu
  check_input: Zkontrolujte prosím zadané hodnoty, některá pole nemají platnou hodnotu.
  cannot_edit_duplicated: Tyto přihlašovací údaje kolidují s jinými (stejná organizace, platforma a verze COUNTER). Dokud nebude konflikt vyřešen smazáním konfliktních údajů, nepůjde tyto údaje upravit.
  cannot_create_duplicated: CELUS nepodporuje více přihlašovacích údajů pro stejnou organizaci, platformu a verzi COUNTER.
  multiple_credentials_info_link: Více informací o zdvojených přihlašovacích údajích najdete v {link}.
  this_article: tomto článku
  show_debug: Zobrazit debug informace
  sushi_debug_links: Sushi debug odkazy
  no_report_selected: Nebyl vybrán žádný report
  last_harvestable_month: Poslední stáhnutelný měsíc
  last_harvestable_month_tt: |
    Pokud víte, že data nejsou dostupná před určitým datem, můžete toto datum nastavit zde. CELUS bude tuto informaci používat a
    nebude se snažit data stáhnout před tímto datem.
  last_harvestable_month_tt_disabled: Pro výběr posledního stáhnutelného měsíce vyberte alespoň jeden typ reportu.
  auto_update_url_text_off: Nastavit URL ručně
  auto_update_url_text_on: URL bude nastavena automaticky z metadat platformy
  auto_update_url_hint: URL je automaticky spravována CELUSem na základě metadat platformy
  counter_report_from_platform_text_off: Nastavit typy reportů ručně
  counter_report_from_platform_text_on: Typy reportů budou nastaveny automaticky z metadat platformy
  counter_report_from_platform_hint: Typy reportů budou automaticky spravovány CELUSem na základě metadat platformy
  counter_report_from_empty_platform_hint: Platforma nedefinuje žádné reporty pro zadanou verzi COUNTERu. Nastavte je prosím ručně.
  edit_platform_tooltip: Editovat platformu
</i18n>

<template>
  <v-sheet>
    <v-form v-model="valid" ref="form">
      <v-card>
        <v-card-title class="headline d-flex"
          >{{ $t("title.edit_sushi_credentials") }}
          <v-spacer></v-spacer>
          <v-tooltip
            location="bottom"
            max-width="600px"
            v-if="canShowDebugLinks"
          >
            <template #activator="{ props }">
              <v-icon
                size="x-small"
                color="grey"
                class="mr-2"
                @click="toggleDebug"
                v-bind="props"
              >
                {{ showDebug ? "fa fa-angle-up" : "fa fa-angle-down" }}
              </v-icon>
            </template>
            <span>{{ $t("show_debug") }}</span>
          </v-tooltip>
        </v-card-title>
        <v-card-text>
          <!-- debug info -->
          <v-sheet
            v-if="canShowDebugLinks && showDebug"
            class="text-right mx-2 mb-2"
          >
            <span>{{ $t("sushi_debug_links") }}:</span>
            <v-chip
              v-for="rt in selectedReportTypeObjs"
              :key="rt.id"
              :href="sushiUrl(rt)"
              target="_blank"
              color="info"
              class="ml-2"
              label
            >
              {{ rt.code }}
              <v-icon
                size="x-small"
                class="ml-2"
                icon="fas fa-external-link-alt"
              ></v-icon>
            </v-chip>
            <span v-if="selectedReportTypes.length === 0" class="pl-1">{{
              $t("no_report_selected")
            }}</span>
          </v-sheet>
          <!-- alert about conflicting credentials -->
          <v-alert
            v-if="conflictingCredentials"
            type="error"
            variant="outlined"
          >
            <p v-if="credentials">{{ $t("cannot_edit_duplicated") }}</p>
            <p v-else>{{ $t("cannot_create_duplicated") }}</p>
            <p>
              <i18n-t keypath="multiple_credentials_info_link">
                <template v-slot:link>
                  <a
                    href="https://support.celus.net/support/solutions/articles/103000063863"
                    target="_blank"
                    >{{ $t("this_article") }}</a
                  >
                </template>
              </i18n-t>
            </p>
          </v-alert>
          <v-alert
            v-else-if="credentials && credentials.broken"
            type="error"
            variant="outlined"
          >
            <p class="bold">{{ $t("broken") }}</p>
            <p>{{ $t("broken_unbreak_manually") }}</p>
            <div>
              <v-btn
                color="error"
                variant="outlined"
                class="mt-4"
                @click="markFixed()"
                >{{ $t("mark_fixed") }}</v-btn
              >
            </div>
          </v-alert>
          <v-alert
            v-else-if="credentials && !credentials.verified"
            type="warning"
            variant="outlined"
          >
            <p class="bold top_alert">{{ $t("unverified_title") }}</p>
            <p class="top_alert">{{ $t("unverified_details") }}</p>
            <p class="top_alert">{{ $t("unverified_note") }}</p>
            <div>
              <v-btn
                color="warning"
                variant="outlined"
                @click="showTestDialog = true"
                >{{ $t("plan_harvest") }}</v-btn
              >
            </div>
          </v-alert>
          <v-container fluid class="pb-0">
            <v-row>
              <v-col cols="12" :md="4">
                <v-tooltip location="bottom" max-width="600px">
                  <template #activator="{ props }">
                    <v-text-field
                      v-model="title"
                      v-bind="props"
                      :label="$t('title_label')"
                      density="compact"
                      height="2.75rem"
                    ></v-text-field>
                  </template>

                  {{ $t("title_tooltip") }}
                </v-tooltip>
              </v-col>
              <v-col cols="12" :md="4">
                <v-text-field
                  v-if="credentials"
                  :label="$t('organization')"
                  disabled
                  density="compact"
                  height="2.75rem"
                  :model-value="organization.name"
                >
                </v-text-field>
                <v-select
                  v-else
                  v-model="organization"
                  :items="organizations"
                  item-title="name"
                  :label="$t('organization')"
                  return-object
                  :disabled="organizationSelected"
                  :rules="[rules.required]"
                  density="compact"
                  height="2.75rem"
                  :menu-props="{ maxHeight: 480 }"
                >
                </v-select>
              </v-col>
              <v-col cols="12" :md="4">
                <span class="d-flex">
                  <v-text-field
                    v-if="credentials || fixedPlatform"
                    :label="$t('platform')"
                    disabled
                    density="compact"
                    height="2.75rem"
                    :model-value="activePlatformName"
                  >
                    <template #default v-if="editablePlatform">
                      <v-tooltip location="bottom">
                        <template #activator="{ props }">
                          <v-btn
                            density="comfortable"
                            v-bind="props"
                            class="edit-platform pb-0 mb-0"
                            size="x-small"
                            :elevation="0"
                            variant="plain"
                            color="primary"
                            icon="fa fa-edit"
                            @click="showPlatformEditDialog = true"
                          ></v-btn>
                        </template>
                        {{ $t("edit_platform_tooltip") }}
                      </v-tooltip>
                    </template>
                  </v-text-field>
                  <PlatformSelector
                    v-else
                    :platforms="platforms"
                    v-model="platform"
                    :label="$t('platform')"
                    :loading="loadingPlatforms"
                    return-object
                    class="platform_select"
                    ref="platformField"
                  >
                    <template
                      #prepend
                      v-if="
                        allowUserCreatePlatforms &&
                        (!credentials || !credentials.pk)
                      "
                    >
                      <v-list-item>
                        <v-list-item-title>
                          <AddPlatformButton
                            @update-platforms="preselectCreatedPlatform"
                            :text="true"
                            small
                            color="success"
                            class="pl-1"
                          />
                        </v-list-item-title>
                      </v-list-item>
                    </template>
                  </PlatformSelector>

                  <v-tooltip location="bottom" v-if="platformRegistryLink">
                    <template #activator="{ props }">
                      <span v-bind="props" class="align-self-end mb-5 ms-1">
                        <a
                          target="_blank"
                          :href="`${registryUrlBase}platform/${activePlatform.counter_registry_id}/`"
                          style="line-height: 2rem"
                        >
                          <v-icon size="small" color="counterRegistry"
                            >fas fa-external-link-alt
                          </v-icon>
                        </a>
                      </span>
                    </template>
                    <span>{{ $t("registry_link") }}</span>
                  </v-tooltip>
                </span>
              </v-col>
            </v-row>
            <v-row>
              <v-col cols="12" :sm="counterVersion5X ? 4 : 6">
                <v-text-field
                  v-model="requestorId"
                  :label="$t('labels.requestor_id')"
                  :disabled="!activePlatform"
                  persistent-hint
                  :hint="requestorIdInfo ? $t('see_registry_hint') : ''"
                >
                  <template #append-inner v-if="requestorIdInfo">
                    <RegistryIcon :text="requestorIdInfo"></RegistryIcon>
                  </template>
                </v-text-field>
              </v-col>
              <v-col cols="12" :sm="counterVersion5X ? 4 : 6">
                <v-text-field
                  v-model="customerId"
                  :label="$t('labels.customer_id')"
                  :rules="[rules.required]"
                  :disabled="!activePlatform"
                  persistent-hint
                  :hint="customerIdInfo ? $t('see_registry_hint') : ''"
                >
                  <template #append-inner v-if="customerIdInfo">
                    <RegistryIcon :text="customerIdInfo"></RegistryIcon>
                  </template>
                </v-text-field>
              </v-col>

              <v-col v-if="counterVersion5X" cols="12" :sm="4">
                <v-text-field
                  v-model="apiKey"
                  :label="$t('labels.api_key')"
                  :disabled="!activePlatform"
                  :rules="[ruleAPIkey]"
                  persistent-hint
                  :hint="apiKeyInfo ? $t('see_registry_hint') : ''"
                >
                  <template #append-inner>
                    <RegistryIcon
                      v-if="apiKeyInfo"
                      :text="apiKeyInfo"
                    ></RegistryIcon>
                  </template>
                </v-text-field>
              </v-col>
            </v-row>
            <v-row>
              <v-col cols="6" sm="3" md="2">
                <v-select
                  v-model="counterVersion"
                  :label="$t('labels.counter_version')"
                  :items="allowedCounterVersions"
                  :disabled="!!credentials || !activePlatform"
                  :no-data-text="$t('all_versions_used')"
                  :rules="[ruleNoConflictingCredentials]"
                  ref="counterVersionField"
                >
                </v-select>
              </v-col>
              <v-col cols="12" sm="9" md="5">
                <v-text-field
                  v-model="url"
                  :label="$t('labels.url')"
                  :placeholder="this.urlPlaceholder"
                  :rules="[
                    rules.required,
                    ruleUrlValid,
                    ruleUrlHttps,
                    ruleUrlC5NoReport,
                    ruleUrlC5NoQueryParams,
                  ]"
                  validate-on-blur
                  :error-messages="errors.url"
                  :disabled="
                    !activePlatform ||
                    (autoUpdateUrl && !!currentKnowledgebaseUrl)
                  "
                  ref="urlField"
                  :hint="
                    currentKnowledgebaseUrl && autoUpdateUrl
                      ? $t('auto_update_url_hint')
                      : ''
                  "
                  :persistent-hint="currentKnowledgebaseUrl && autoUpdateUrl"
                  @update:modelValue="urlManuallyEdited = true"
                >
                  <template #append v-if="currentKnowledgebaseUrl">
                    <v-tooltip location="bottom" max-width="400">
                      <template v-slot:activator="{ props }">
                        <v-btn
                          color="primary"
                          variant="plain"
                          icon
                          @click="toggleAutoUpdateUrl"
                          size="small"
                          v-bind="props"
                        >
                          <v-icon size="small"
                            >fa
                            {{ autoUpdateUrl ? "fa-edit" : "fa-book" }}</v-icon
                          >
                        </v-btn>
                      </template>
                      <span
                        >{{
                          autoUpdateUrl
                            ? $t("auto_update_url_text_off")
                            : $t("auto_update_url_text_on")
                        }}
                      </span>
                    </v-tooltip>
                  </template>
                </v-text-field>
              </v-col>
              <v-col cols="12" md="5" class="active_report">
                <v-autocomplete
                  v-if="reportTypes.length"
                  density="comfortable"
                  v-model="selectedReportTypes"
                  :items="reportTypesSorted"
                  :label="$t('active_report_types')"
                  multiple
                  item-title="code"
                  item-value="id"
                  :rules="[rules.atLeastOne]"
                  :loading="loadingReportTypes"
                  :disabled="
                    !activePlatform ||
                    (useCounterReportsFromPlatform &&
                      reportTypesFromPlatform.length > 0)
                  "
                  ref="selectedReportTypesField"
                  :hint="reportTypeSelectorHint"
                  :persistent-hint="useCounterReportsFromPlatform"
                >
                  <template #item="{ props, item }">
                    <v-list-item
                      v-bind="props"
                      title
                      :disabled="isBlacklisted(item.raw)"
                    >
                      <template v-slot:default>
                        <SushiReportIndicator
                          :report="item.raw"
                          :broken-fn="isBroken"
                          :knowledgebase-fn="inKnowledgebase"
                          :registry-fn="inRegistry"
                          :blacklisted-fn="isBlacklisted"
                          show-name
                        ></SushiReportIndicator>
                      </template>
                    </v-list-item>
                  </template>
                  <template #selection="{ item, props, selected }">
                    <v-chip
                      v-bind="props"
                      :model-value="selected"
                      size="small"
                      label
                      variant="flat"
                      :color="isBroken(item.raw) ? 'secondary' : 'primary'"
                    >
                      <SushiReportIndicator
                        :report="item.raw"
                        :broken-fn="isBroken"
                        :knowledgebase-fn="inKnowledgebase"
                        :registry-fn="inRegistry"
                        :blacklisted-fn="isBlacklisted"
                        is-autocomplete
                      ></SushiReportIndicator>
                    </v-chip>
                  </template>
                  <template #append>
                    <v-tooltip
                      location="bottom"
                      max-width="400"
                      v-if="reportTypesFromPlatform.length > 0"
                    >
                      <template v-slot:activator="{ props }">
                        <v-btn
                          color="primary"
                          variant="plain"
                          icon
                          @click="toggleUseCounterReportsFromPlatform"
                          size="small"
                          v-bind="props"
                        >
                          <v-icon size="small"
                            >fa
                            {{
                              useCounterReportsFromPlatform
                                ? "fa-edit"
                                : "fa-book"
                            }}</v-icon
                          >
                        </v-btn>
                      </template>
                      <span
                        >{{
                          useCounterReportsFromPlatform
                            ? $t("counter_report_from_platform_text_off")
                            : $t("counter_report_from_platform_text_on")
                        }}
                      </span>
                    </v-tooltip>
                    <v-tooltip location="bottom" max-width="600px">
                      <template #activator="{ props }">
                        <div class="calendar_button" v-bind="props">
                          <v-btn
                            :color="
                              lastHarvestableMonthUpdated ? 'info' : 'primary'
                            "
                            @click="showLastHarvestableMonthDialog = true"
                            size="small"
                            icon="fas fa-calendar-alt"
                            variant="plain"
                            class="button_append"
                            :disabled="selectedReportTypes.length === 0"
                          >
                          </v-btn>
                        </div>
                      </template>
                      {{
                        selectedReportTypes.length === 0
                          ? $t("last_harvestable_month_tt_disabled")
                          : $t("last_harvestable_month_tt")
                      }}
                    </v-tooltip>
                  </template>
                </v-autocomplete>
              </v-col>
            </v-row>
            <v-row class="pb-3 mx-0 pt-2">
              <v-col class="pb-4 subdued-section">
                <v-tooltip location="bottom" max-width="600px">
                  <template #activator="{ props }">
                    <h4
                      v-bind="!counterVersion5X ? props : null"
                      class="font-weight-light pl-2"
                      v-text="$t('extra_attributes')"
                    ></h4>
                  </template>
                  {{ $t("extra_attributes_tooltip") }}
                </v-tooltip>
                <v-container fluid class="pa-0 pl-md-8 mt-3">
                  <v-row v-if="counterVersion5X">
                    <v-col md="6" class="pt-0">
                      <v-text-field
                        v-model="platformFilter"
                        :label="$t('labels.platform_filter')"
                        :disabled="!activePlatform"
                        :rules="[rulePlatform]"
                        persistent-hint
                        class="mb-3 pb-3"
                        :hint="
                          platformAttrRequired
                            ? $t('registry_platform_required')
                            : ''
                        "
                        @update:modelValue="platformFilterManuallyEdited = true"
                      >
                        <template v-slot:append-inner>
                          <v-tooltip location="right" max-width="400px">
                            <template #activator="{ props }">
                              <v-icon
                                v-bind="props"
                                size="small"
                                :color="
                                  platformAttrRequired
                                    ? 'counterRegistry'
                                    : 'secondary'
                                "
                                >{{
                                  platformAttrRequired
                                    ? "fa fa-registered"
                                    : "fa fa-info-circle"
                                }}</v-icon
                              >
                            </template>
                            <div>
                              <div v-if="platformAttrRequired" class="bold">
                                {{ $t("registry_info") }}
                              </div>
                              <div
                                v-html="
                                  platformAttrRequired
                                    ? platformAttrInfo ||
                                      $t('registry_platform_required')
                                    : $t('platform_filter_tooltip')
                                "
                              ></div>
                            </div>
                          </v-tooltip>
                        </template>
                      </v-text-field>
                    </v-col>
                  </v-row>
                  <div v-if="!counterVersion5X">
                    <v-row>
                      <v-col cols="auto" class="mt-6 py-0">
                        <span class="font-weight-light">{{
                          $t("labels.http_authentication")
                        }}</span>
                      </v-col>
                      <v-col md="3" class="py-0">
                        <v-text-field
                          v-model="httpUsername"
                          :label="$t('labels.http_username')"
                          :disabled="!activePlatform"
                        >
                        </v-text-field>
                      </v-col>
                      <v-col md="4" class="py-0">
                        <v-text-field
                          v-model="httpPassword"
                          :label="$t('labels.http_password')"
                          :disabled="!activePlatform"
                        >
                        </v-text-field>
                      </v-col>
                    </v-row>
                    <v-row v-for="(param, index) in extraParams" :key="index">
                      <v-col cols="10" sm="4" md="3" class="py-0">
                        <v-text-field
                          v-model="param.key"
                          :label="$t('labels.variable')"
                          :rules="[rules.required, ruleExtraNoDuplicateKey]"
                          :disabled="!activePlatform"
                        >
                        </v-text-field>
                      </v-col>
                      <v-col cols="10" sm="6" md="5" class="py-0">
                        <v-text-field
                          v-model="param.value"
                          :label="$t('labels.variable_value')"
                          :rules="[rule.required]"
                          :disabled="!activePlatform"
                        >
                        </v-text-field>
                      </v-col>
                      <v-col cols="auto">
                        <v-btn
                          @click="removeExtraParam(index)"
                          variant="text"
                          icon
                          color="error"
                        >
                          <v-icon>fa fa-times</v-icon>
                        </v-btn>
                      </v-col>
                    </v-row>
                    <v-row>
                      <v-col cols="12" class="py-0">
                        <v-tooltip location="bottom">
                          <template #activator="{ props }">
                            <v-btn
                              v-bind="props"
                              @click="addExtraParam()"
                              variant="outlined"
                              text
                              color="secondary"
                              :disabled="!activePlatform"
                            >
                              <v-icon left size="x-small">fa fa-plus</v-icon>
                              {{ $t("add_custom_param") }}
                            </v-btn>
                          </template>
                          {{ $t("add_custom_param_tooltip") }}
                        </v-tooltip>
                      </v-col>
                    </v-row>
                  </div>
                </v-container>
              </v-col>
            </v-row>
            <v-row v-if="ipAuthorizationRequired">
              <v-col cols="12" class="py-0">
                <v-alert type="warning" variant="outlined">
                  {{ $t("ip_authorization_required") }}

                  <HarvesterIPAddressList></HarvesterIPAddressList>
                </v-alert>
              </v-col>
            </v-row>
            <v-row>
              <v-col v-if="anyBrokenReports">
                <v-alert type="warning" variant="outlined" class="mb-0">
                  <p>{{ $t("broken_reports_warning") }}</p>
                  <v-btn
                    color="warning"
                    variant="outlined"
                    @click="markFixed(true)"
                    class="mt-4"
                    >{{ $t("mark_fixed") }}</v-btn
                  >
                </v-alert>
              </v-col>
            </v-row>
          </v-container>
        </v-card-text>
        <v-card-actions>
          <v-container fluid class="pt-2">
            <v-row no-gutters align="center">
              <v-col cols="auto">
                <v-tooltip location="bottom">
                  <template v-slot:activator="{ props }">
                    <span v-bind="props">
                      <v-switch
                        v-model="enabled"
                        :label="$t('sushi.enabled')"
                        class="pl-2 my-0"
                        color="primary"
                        :disabled="!activePlatform"
                        hide-details
                      ></v-switch>
                    </span>
                  </template>
                  <span>{{ $t("sushi.enabled_tooltip") }}</span>
                </v-tooltip>
              </v-col>
              <v-col cols="auto" class="ml-6" v-if="consortialInstall">
                <v-tooltip location="bottom">
                  <template v-slot:activator="{ props }">
                    <span v-bind="props">
                      <v-switch
                        v-model="outsideConsortium"
                        :label="$t('outside')"
                        color="primary"
                        class="pl-2 my-0"
                        :disabled="!showManagementStuff || !activePlatform"
                        hide-details
                      ></v-switch>
                    </span>
                  </template>
                  <span>
                    {{ $t("outside_tooltip") }}
                    {{
                      showManagementStuff ? "" : $t("only_managers_can_change")
                    }}
                  </span>
                </v-tooltip>
              </v-col>
              <v-spacer></v-spacer>
              <v-col cols="auto">
                <DeleteSushiCredentialsDataWidget
                  v-if="credentials"
                  :class="!$vuetify.display.xs ? 'mr-8' : 'mr-2'"
                  :credentials="credentials"
                  :platform="activePlatform"
                  @deleted="
                    $emit('deleted', { id: credentials.pk });
                    $emit('update:modelValue', false);
                  "
                ></DeleteSushiCredentialsDataWidget>
                <v-btn
                  @click="closeDialog"
                  class="mr-2"
                  variant="elevated"
                  color="defaultButton"
                >
                  <v-icon size="small" class="mr-2">fa fa-times</v-icon>
                  {{ $t("close") }}
                </v-btn>
                <v-btn
                  color="primary"
                  @click="saveAndClose()"
                  variant="elevated"
                  :disabled="saving || disableSave"
                  :loading="saving"
                >
                  <v-icon size="small" class="mr-2">fa fa-save</v-icon>
                  {{ $t("save") }}
                </v-btn>
              </v-col>
            </v-row>
          </v-container>
        </v-card-actions>

        <v-dialog v-model="showTestDialog" max-width="1200px">
          <v-card>
            <v-card-title>{{ $t("test_dialog") }}</v-card-title>
            <v-card-text>
              <HarvestSelectedWidget
                v-if="showTestDialog"
                :credentials="[credentials]"
                ref="testWidget"
                test
              >
              </HarvestSelectedWidget>
            </v-card-text>
            <v-card-actions>
              <v-spacer></v-spacer>
              <v-btn
                @click="stopTestDialog()"
                variant="elevated"
                color="defaultButton"
                class="ma-4"
                >{{ $t("close") }}</v-btn
              >
            </v-card-actions>
          </v-card>
        </v-dialog>
        <v-dialog v-model="showLastHarvestableMonthDialog" max-width="500px">
          <LastHarvestableMonthWidget
            :credentials="[credentials]"
            @close="showLastHarvestableMonthDialog = false"
            @apply="applyLastHarvestableMonthDialog"
          ></LastHarvestableMonthWidget>
        </v-dialog>
        <v-dialog v-model="showPlatformEditDialog" v-if="editablePlatform">
          <PlatformEditDialog
            :platform-id="platform.pk"
            @close="closeEditPlatformDialog"
            @saved="saveAndCloseEditPlatformDialog"
          ></PlatformEditDialog>
        </v-dialog>
      </v-card>
    </v-form>
  </v-sheet>
</template>

<script>
import AddPlatformButton from "@/components/AddPlatformButton";
import PlatformEditDialog from "@/components/PlatformEditDialog";
import PlatformSelector from "@/components/selectors/PlatformSelector.vue";
import DeleteSushiCredentialsDataWidget from "@/components/sushi/DeleteSushiCredentialsDataWidget";
import HarvesterIPAddressList from "@/components/sushi/HarvesterIPAddressList";
import HarvestSelectedWidget from "@/components/sushi/HarvestSelectedWidget";
import LastHarvestableMonthWidget from "@/components/sushi/LastHarvestableMonthWidget";
import RegistryIcon from "@/components/sushi/RegistryIcon";
import SushiReportIndicator from "@/components/sushi/SushiReportIndicator";
import { counterVersionToStr, testSushiUrlReport } from "@/libs/sushi";
import formRulesMixin from "@/mixins/formRulesMixin";
import axios from "axios";
import validate from "validate.js";
import { mapActions, mapGetters } from "vuex";

export default {
  name: "SushiCredentialsEditDialog",

  mixins: [formRulesMixin],

  components: {
    PlatformEditDialog,
    PlatformSelector,
    LastHarvestableMonthWidget,
    HarvesterIPAddressList,
    RegistryIcon,
    HarvestSelectedWidget,
    SushiReportIndicator,
    AddPlatformButton,
    DeleteSushiCredentialsDataWidget,
  },
  props: {
    credentialsObject: {},
    modelValue: { default: false, type: Boolean },
    fixedPlatform: { required: false, type: Number },
  },
  data() {
    const credentials = this.credentialsObject;
    let extraParams = [];
    let platformFilter = "";
    let sortedReportTypes = [];
    if (credentials) {
      for (let [key, value] of Object.entries(credentials.extra_params)) {
        if (
          key === "platform" &&
          [5, 51].includes(credentials.counter_version)
        ) {
          platformFilter = value;
        } else {
          extraParams.push({ key: key, value: value });
        }
      }
      sortedReportTypes = [...credentials.counter_reports_long];
      sortedReportTypes.sort((a, b) => a.code.localeCompare(b.code));
    }
    return {
      allReportTypes: [],
      organization: credentials ? credentials.organization : null,
      platform: credentials ? credentials.platform : null,
      requestorId: credentials ? credentials.requestor_id : "",
      customerId: credentials ? credentials.customer_id : "",
      counterVersion: credentials ? credentials.counter_version : 5,
      url: credentials ? credentials.url : "",
      autoUpdateUrl: credentials ? credentials.auto_update_url : true,
      useCounterReportsFromPlatform: credentials
        ? credentials.use_counter_reports_from_platform
        : true,
      urlManuallyEdited: false,
      platformFilterManuallyEdited: false,
      httpUsername: credentials ? credentials.http_username : "",
      httpPassword: credentials ? credentials.http_password : "",
      apiKey: credentials ? credentials.api_key : "",
      platformFilter: platformFilter,
      extraParams: extraParams,
      selectedReportTypes: sortedReportTypes.map((item) => item.id),
      showTestDialog: false,
      showLastHarvestableMonthDialog: false,
      showPlatformEditDialog: false,
      reportToLastHarvestableMonth: null,
      organizations: [],
      platforms: [],
      errors: {},
      savedCredentials: null,
      enabled: credentials ? credentials.enabled : true,
      outsideConsortium: credentials ? credentials.outside_consortium : true,
      title: credentials ? credentials.title : "",
      loadingPlatforms: false,
      loadingReportTypes: false,
      lastHarvestableMonthUpdated: false,
      lastHarvestableMonth: credentials
        ? credentials.last_harvestable_month
        : null,
      valid: false,
      saving: false,
      useCasesData: [],
      prefixApiKey: "",
      prefixPlatform: "",
      initializing: true,
      showDebug: false,
      registryUrlBase: "https://registry.countermetrics.org/",
      existingCredentials: [],
    };
  },
  computed: {
    ...mapGetters({
      selectedOrganization: "selectedOrganization",
      organizationSelected: "organizationSelected",
      consortialInstall: "consortialInstall",
      allowUserCreatePlatforms: "allowUserCreatePlatforms",
      debugMonth: "dateRangeCoverageEndText",
      showManagementStuff: "showManagementStuff",
      contactEmail: "contactEmail",
    }),
    credentials() {
      if (this.credentialsObject) {
        return this.credentialsObject;
      }
      if (this.savedCredentials) {
        return this.savedCredentials;
      }
      return null;
    },
    activePlatform() {
      if (this.credentials) {
        return this.credentials.platform;
      } else if (this.fixedPlatform) {
        const found = this.platforms.find(
          (item) => item.pk === this.fixedPlatform,
        );
        if (found) {
          return found;
        }
      }
      return this.platform;
    },
    activePlatformId() {
      if (this.activePlatform) {
        return this.activePlatform.pk;
      }
      return null;
    },
    apiData() {
      let extraParams = {};
      for (let rec of this.extraParams) {
        if (rec.key.trim()) extraParams[rec.key] = rec.value;
      }
      if (this.counterVersion5X && this.platformFilter.trim()) {
        extraParams.platform = this.platformFilter.trim();
      }
      const autoUpdateUrl =
        this.autoUpdateUrl && !!this.currentKnowledgebaseUrl;
      let data = {
        title: this.title,
        customer_id: this.customerId,
        requestor_id: this.requestorId,
        api_key: this.apiKey,
        counter_version: this.counterVersion,
        auto_update_url: autoUpdateUrl,
        use_counter_reports_from_platform:
          this.useCounterReportsFromPlatform &&
          this.reportTypesFromPlatform.length > 0,
        http_username: this.httpUsername,
        http_password: this.httpPassword,
        extra_params: extraParams,
        counter_reports: this.selectedReportTypes,
        enabled: this.enabled,
        outside_consortium: this.outsideConsortium,
      };
      if (autoUpdateUrl) {
        data.url = this.currentKnowledgebaseUrl;
      } else {
        data.url = this.url;
      }
      if (this.credentials) {
        data.id = this.credentials.pk;
      } else {
        data.platform_id = this.platform.pk;
        data.organization_id = this.organization.pk;
      }
      if (this.lastHarvestableMonthUpdated) {
        data.last_harvestable_month = this.lastHarvestableMonth || null;
      }
      return data;
    },
    reportTypes() {
      return this.allReportTypes.filter(
        (item) => item.counter_version === this.counterVersion,
      );
    },
    currentKnowledgebase() {
      if (this.activePlatform) {
        return this.activePlatform.knowledgebase;
      } else {
        return null;
      }
    },
    currentKnowledgebaseUrl() {
      const providers = (this.currentKnowledgebase?.providers || []).filter(
        (provider) => provider.counter_version === this.counterVersion,
      );
      // Note that knowledgebase should contain only a single provider
      // per counter version
      return providers.length > 0 ? providers[0].provider?.url : null;
    },
    currentUseCases() {
      if (this.activePlatform) {
        return this.useCasesData.filter(
          (e) =>
            e.platform === this.activePlatform.pk &&
            e.counter_version === this.counterVersion,
        );
      } else {
        return [];
      }
    },
    pickedUseCases() {
      // Use usecases from selected organization
      // or use all if no such usecases exists
      if (this.organization?.pk) {
        let res = this.currentUseCases.filter(
          (e) => e.organization === this.organization.pk,
        );
        if (res.length > 0) {
          return res;
        }
      }
      return this.currentUseCases;
    },
    useCaseReportTypes() {
      let report_type_ids = [
        ...new Set(this.pickedUseCases.map((e) => e.counter_report)),
      ];

      // Convert id to code
      return report_type_ids.flatMap((e) => {
        for (const crt of this.allReportTypes) {
          if (crt.id === e) {
            return [crt.code];
          } else {
            return [];
          }
        }
      });
    },
    pickedCaseUrl() {
      // pick latest record
      if (this.pickedUseCases.length > 0) {
        let records = [...this.pickedUseCases];
        records.sort((a, b) =>
          a.latest < b.latest ? 1 : a.latest > b.latest ? -1 : 0,
        );
        return records[0].url;
      }
      return null;
    },
    knowledgebaseProvider() {
      if (this.currentKnowledgebase?.providers) {
        return this.currentKnowledgebase.providers.find(
          (provider) => provider.counter_version == this.counterVersion,
        );
      }
      return null;
    },
    knowledgebaseReportTypes() {
      if (this.knowledgebaseProvider) {
        return this.knowledgebaseProvider.assigned_report_types.map(
          (e) => e.report_type,
        );
      }
      // Fallback to useCases when there is no knowledgebase
      return this.useCaseReportTypes;
    },
    isValid() {
      return this.valid;
    },
    allowedCounterVersions() {
      return [51, 5, 4].map((e) => {
        return { title: counterVersionToStr(e), value: e };
      });
    },
    conflictingCredentials() {
      /*
       * return true if there are credentials with the same organization, platform and counter
       * version - this is not allowed and should be reflected in the UI
       * */
      return this.usedCounterVersions.includes(this.counterVersion);
    },
    usedCounterVersions() {
      // return list of counter versions that are used by other credentials
      // for the same organization and platform
      if (this.existingCredentials) {
        return this.existingCredentials
          .filter(
            (cred) =>
              cred.organization.pk === this.organization?.pk &&
              this.platform &&
              cred.platform.pk === this.platform?.pk &&
              (!this.credentials || cred.pk !== this.credentials?.pk),
          )
          .map((cred) => cred.counter_version);
      }
      return [];
    },
    unusedCounterVersions() {
      // return list of counter versions that are not used by other credentials
      // for the same organization and platform
      return this.allowedCounterVersions
        .map((cv) => cv.value)
        .filter((cv) => !this.usedCounterVersions.includes(cv));
    },
    platformsBaseUrl() {
      if (this.organization?.pk) {
        return `/api/organization/${this.organization.pk}/all-platform/`;
      }
      return null;
    },
    useCasesUrl() {
      if (this.platformsBaseUrl) {
        return `${this.platformsBaseUrl}use-cases/`;
      }
      return null;
    },
    brokenReports() {
      if (this.credentials) {
        return this.selectedReportTypes.filter((item) =>
          this.isBroken({ id: item }),
        );
      }
      return [];
    },
    anyBrokenReports() {
      return this.brokenReports.length > 0;
    },
    urlPlaceholder() {
      switch (this.counterVersion) {
        case 4:
          return "https://counter4.example.com";
        case 5:
        case 51:
          return "https://sushi.example.com";
        default:
          return "";
      }
    },
    activePlatformName() {
      if (this.activePlatform)
        return this.activePlatform.name || this.activePlatform.short_name;
      return "";
    },
    platformRegistryLink() {
      if (this.activePlatform && this.activePlatform.counter_registry_id) {
        return `${this.registryUrlBase}api/v1/platform/${this.activePlatform.counter_registry_id}/`;
      }
      return null;
    },
    registrySushiService() {
      if (this.activePlatform && this.activePlatform.registry_data) {
        return this.activePlatform.registry_data.sushi_services.find(
          (service) => service.counter_release == this.counterVersionStr,
        );
      }
      return null;
    },
    requestorIdInfo() {
      if (!this.requestorIdRequired) {
        return this.$t("requestor_id_not_required");
      }
      return this.registrySushiService?.requestor_id_info ?? "";
    },
    requestorIdRequired() {
      return this.registrySushiService?.requestor_id_required ?? true;
    },
    customerIdInfo() {
      return this.registrySushiService?.customer_id_info ?? "";
    },
    apiKeyInfo() {
      return this.registrySushiService?.api_key_info ?? "";
    },
    ipAuthorizationRequired() {
      return this.registrySushiService?.ip_address_authorization ?? false;
    },
    platformAttrRequired() {
      return this.registrySushiService?.platform_attr_required ?? false;
    },
    platformAttrInfo() {
      return this.registrySushiService?.platform_specific_info ?? "";
    },
    disableSave() {
      // normally we do not disable the save button, but rather show a warning
      // after the user clicks it. But in some cases we can disable it
      // completely because the warning is already shown
      return this.conflictingCredentials;
    },
    selectedReportTypeObjs() {
      return this.allReportTypes.filter((item) =>
        this.selectedReportTypes.includes(item.id),
      );
    },
    canShowDebugLinks() {
      // Links for C4 sushi are not working properly
      return this.counterVersion5X;
    },
    counterVersion5X() {
      return this.counterVersion === 5 || this.counterVersion === 51;
    },
    counterVersionStr() {
      return counterVersionToStr(this.counterVersion);
    },
    editablePlatform() {
      return this.showManagementStuff;
    },
    reportTypesSorted() {
      let reports = [...this.reportTypes];
      reports.sort((a, b) => a.code.localeCompare(b.code));
      return reports;
    },
    reportTypesFromPlatform() {
      if (!this.activePlatform) {
        return [];
      }
      const counter_reports_filtered =
        this.activePlatform.counter_reports_long.filter(
          (e) => e.counter_version === this.counterVersion,
        );
      counter_reports_filtered.sort((a, b) => a.code.localeCompare(b.code));
      return counter_reports_filtered;
    },
    reportTypeSelectorHint() {
      if (this.useCounterReportsFromPlatform) {
        if (this.reportTypesFromPlatform.length > 0) {
          return this.$t("counter_report_from_platform_hint");
        } else {
          return this.$t("counter_report_from_empty_platform_hint");
        }
      } else {
        return "";
      }
    },
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    async loadReportTypes() {
      this.loadingReportTypes = true;
      try {
        let result = await axios.get("/api/counter-report-type/");
        this.allReportTypes = result.data;
        this.updateReportTypeObjects();
      } catch (error) {
        this.showSnackbar({ content: "Error loading report types: " + error });
      } finally {
        this.loadingReportTypes = false;
      }
    },
    updateReportTypeObjects() {
      this.allReportTypes.forEach((item) => {
        item.pk = item.id;
        item.long_name = item.name ? `${item.code}: ${item.name}` : item.code;
      });
    },
    async loadOrganizations() {
      if (this.organizationSelected) {
        // we have a specific organization selected - we use it
        this.organizations = [this.selectedOrganization];
        this.organization = this.selectedOrganization;
      } else {
        try {
          let result = await axios.get("/api/organization/");
          this.organizations = result.data;
          this.organizations.sort((a, b) => a.name.localeCompare(b.name));
          this.organization = this.organizations[0];
        } catch (error) {
          this.showSnackbar({
            content: "Error loading organizations: " + error,
          });
        }
      }
    },
    async loadPlatforms() {
      if (this.platformsBaseUrl) {
        this.platforms = [];
        this.loadingPlatforms = true;
        if (this.fixedPlatform) {
          try {
            let result = await axios.get(
              this.platformsBaseUrl + this.fixedPlatform + "/",
            );
            this.platform = result.data;
            this.platforms = [this.platform];
          } catch (error) {
            this.showSnackbar({
              content:
                `Error loading platform id:${this.fixedPlatform}: ` + error,
            });
          } finally {
            this.loadingPlatforms = false;
          }
        } else {
          try {
            let result = await axios.get(this.platformsBaseUrl);
            this.platforms = result.data;
            this.platforms.sort((a, b) =>
              a.name ? a.name.localeCompare(b.name) : -1,
            );
            if (this.platform) {
              const machingPlatform = this.platforms.find(
                (item) => item.pk === this.platform.pk,
              );
              if (machingPlatform) {
                this.platform = machingPlatform;
              } else {
                this.platform = this.platforms[0];
              }
            }
          } catch (error) {
            this.showSnackbar({ content: "Error loading platforms: " + error });
          } finally {
            this.loadingPlatforms = false;
          }
        }
      }
    },
    async loadUseCases() {
      if (this.useCasesUrl) {
        this.useCasesData = [];
        try {
          let result = await axios.get(this.useCasesUrl);
          this.useCasesData = result.data;
        } catch (error) {
          this.showSnackbar({ content: "Error loading use cases: " + error });
        }
      }
    },
    async preselectCreatedPlatform(platform) {
      await this.loadPlatforms();
      this.platform = platform;
    },
    closeDialog() {
      this.$emit("update:modelValue", false);
      // this.$emit("close-dialog");
    },
    async saveData(forced) {
      forced |= false;
      this.errors = {};
      this.saving = true;
      let response = null;
      const cleanData = JSON.parse(JSON.stringify(this.apiData));
      let data = structuredClone(cleanData);
      if (forced) {
        data.forced = true;
      }
      try {
        if (this.credentials) {
          // we have existing credentials - we patch it
          response = await axios.patch(
            `/api/sushi-credentials/${this.credentials.pk}/`,
            data,
          );
        } else {
          // we create new credentials
          response = await axios.post(`/api/sushi-credentials/`, data);
        }
      } catch (error) {
        // Show warning for same credentials
        let respData = error.response?.data;
        if (
          !forced &&
          respData &&
          respData[0]?.startsWith("Same credentials")
        ) {
          let text_ref =
            respData[0] == "Same credentials exists - globally"
              ? "same_credentials_global_text"
              : "same_credentials_in_org_text";
          const res = await this.$confirm(this.$t(text_ref), {
            title: this.$t("same_credentials_title"),
            buttonTrueText: this.$t("ignore_and_save"),
            buttonFalseText: this.$t("cancel"),
            icon: "fa fa-copy",
            width: 500,
          });
          if (res) {
            // User really wants to save the it
            return await this.saveData(true);
          }
        } else if (respData && respData["non_field_errors"]) {
          this.showSnackbar({
            content: respData["non_field_errors"][0],
            color: "error",
          });
        } else {
          this.showSnackbar({
            content: this.$t("error_saving"),
            color: "error",
          });
          if (error.response != null) {
            this.processErrors(error.response.data);
          }
        }
        return null;
      } finally {
        this.saving = false;
      }

      this.savedCredentials = response.data;
      await this.showSnackbar({
        content: "Successfully saved SUSHI credentials",
        color: "success",
      });
      this.$emit("update-credentials", response.data);
      return response.data;
    },
    async markFixed(markReports) {
      if (this.credentials) {
        let data = { credentials_id: this.credentials.pk };
        if (this.anyBrokenReports && markReports) {
          data.counter_reports = this.brokenReports.map((item) => item.id);
        }
        try {
          let response = await axios.post(
            "/api/sushi-credentials/unset-broken/",
            [{ credentials_id: this.credentials.pk }],
          );
          this.showSnackbar({
            content: this.$t("mark_fixed_success"),
            color: "success",
          });
          this.$emit("update-credentials", response.data[0]);
        } catch (error) {
          this.showSnackbar({
            content: "Error marking SUSHI credentials as fixed: " + error,
            color: "error",
          });
        }
        this.reloadCredentials();
      }
    },
    processErrors(errors) {
      this.errors = errors;
    },
    async saveAndClose() {
      await this.$refs.form.validate();
      if (this.isValid) {
        let data = await this.saveData();
        if (data) {
          if (data.verified) {
            this.$emit("update:modelValue", false);
          } else {
            let text = `${this.$t("unverified_details")}<br /><br />${this.$t(
              "unverified_note",
            )}`;
            const res = await this.$confirm(text, {
              title: this.$t("unverified_title"),
              buttonTrueText: this.$t("plan_harvest"),
              buttonFalseText: this.$t("close"),
              width: 450,
              icon: "fa fa-warning",
              color: "warning",
            });
            if (res) {
              this.showTestDialog = true;
            } else {
              this.$emit("update:modelValue", false);
            }
          }
        }
      } else {
        this.showSnackbar({
          content: this.$t("check_input"),
          color: "warning",
        });
      }
    },
    stopTestDialog() {
      if (this.$refs.testWidget) {
        this.$refs.testWidget.clean();
      }
      this.showTestDialog = false;
    },
    isBroken(report) {
      if (this.credentials) {
        for (let rt of this.credentials.counter_reports_long) {
          if (rt.id === report.id) {
            return !!rt.broken;
          }
        }
      }
      return false;
    },
    inKnowledgebase(report) {
      return this.knowledgebaseReportTypes.includes(report.code);
    },
    inRegistry(report) {
      const reports = this.activePlatform?.registry_data?.reports;
      if (reports) {
        return !!reports.find(
          (item) =>
            // make sure 5.1 is converted to 51 which is used internally
            item.counter_release.replace(".", "") == this.counterVersion &&
            item.report_id == report.code,
        );
      }
      return false;
    },
    isBlacklisted(report) {
      if (!report.requires_whitelisting) {
        return false;
      }
      if (this.knowledgebaseProvider) {
        return !this.knowledgebaseProvider.assigned_report_types.find(
          (e) => e.report_type == report.code && e.whitelisted,
        );
      }
      return true;
    },
    guessUrl() {
      if (!this.url) {
        // reset edited state for empty urls
        this.urlManuallyEdited = false;
      }

      if (this.urlManuallyEdited) {
        // don't guess URL for manually edited values
        return;
      }

      this.url = "";
      if (this.currentKnowledgebase) {
        this.url = this.currentKnowledgebaseUrl;
        let providers = (this.currentKnowledgebase.providers || []).filter(
          (provider) => provider.counter_version === this.counterVersion,
        );
        if (providers.length > 0) {
          // provider found lets perform update
          this.url = providers[0].provider.url;
          return;
        }
      } else if (this.pickedCaseUrl) {
        this.url = this.pickedCaseUrl;
      }
    },
    guessPlatformFilter() {
      if (!this.platformFilter) {
        // reset edited state
        this.platformFilterManuallyEdited = false;
      }

      if (this.platformFilterManuallyEdited) {
        // don't guess platfrom_filter for manually edited values
        return;
      }

      this.platformFilter = "";
      if (this.currentKnowledgebase) {
        this.platformFilter = this.currentKnowledgebase?.platform_filter || "";
      }
    },
    addExtraParam() {
      this.extraParams.push({ key: "", value: "" });
    },
    removeExtraParam(index) {
      this.extraParams.splice(index, 1);
    },
    ruleAPIkey(modelValue) {
      let pattern = /api_?key[:=]/i;
      let isMatch = pattern.test(modelValue);
      if (isMatch) {
        this.prefixApiKey = pattern.exec(modelValue)[0];
      } else {
        this.prefixApiKey = "";
      }
      return (
        !isMatch ||
        `Please remove the "${this.prefixApiKey}" part of your input.`
      );
    },
    rulePlatform(modelValue) {
      let pattern = /platform[:=]/i;
      let isMatch = pattern.test(modelValue);
      if (isMatch) {
        this.prefixPlatform = pattern.exec(modelValue)[0];
      } else {
        this.prefixPlatform = "";
      }
      return (
        !isMatch ||
        `Please remove the "${this.prefixPlatform}" part of your input.`
      );
    },
    ruleExtraNoDuplicateKey(modelValue) {
      return (
        this.extraParams.filter((item) => item.key.trim() === modelValue.trim())
          .length <= 1 || this.$t("duplicate")
      );
    },
    ruleNoConflictingCredentials() {
      if (this.conflictingCredentials) {
        return this.$t("credentials_conflict_hint");
      }
      return true;
    },
    ruleUrlC5NoReport() {
      if (this.counterVersion5X && !testSushiUrlReport(this.url))
        return this.$t("url_hint_no_report");
      return true;
    },
    ruleUrlC5NoQueryParams() {
      try {
        let parsed = new URL(this.url);
        if (parsed.search) {
          return this.$t("url_hint_no_query", { search: parsed.search });
        }
      } catch (error) {
        return true;
      }
      return true;
    },
    ruleUrlValid() {
      const result = validate(
        { website: this.url },
        { website: { url: { allowLocal: true } } },
      );
      if (result && result.website) {
        return this.$t("invalid_url");
      }
      return true;
    },
    ruleUrlHttps() {
      if (this.url && this.url.toLowerCase().startsWith("http://")) {
        return this.$t("url_must_use_https");
      }
      return true;
    },
    async reloadCredentials() {
      try {
        let response = await axios.get(
          `/api/sushi-credentials/${this.credentials.pk}/`,
        );
        this.savedCredentials = response.data;
        this.$emit("update-credentials", this.savedCredentials);
      } catch (error) {
        this.showSnackbar({
          content: "Error reloading credentials",
          color: "error",
        });
      }
    },
    async loadRegistryData() {
      if (this.platformRegistryLink) {
        try {
          const platformId = this.activePlatform.counter_registry_id;
          let resp = await axios.get(this.platformRegistryLink);
          if (resp.data.id === platformId) {
            // check that the ID did not change during the request
            this.activePlatform.registry_data = resp.data;
          }
        } catch (error) {
          this.showSnackbar({
            content: "Could not load data from the COUNTER registry",
            color: "warning",
          });
        }
      }
    },
    async loadExistingCredentials() {
      const url = `/api/sushi-credentials/?simple=true&organization=${
        this.selectedOrganization ? this.selectedOrganization.pk : "-1"
      }`;
      try {
        let response = await axios.get(url);
        this.existingCredentials = response.data.results;
      } catch (error) {
        this.showSnackbar({
          content: "Error loading credentials list: " + error,
          color: "error",
        });
      }
    },
    toggleDebug() {
      this.showDebug = !this.showDebug;
    },
    sushiUrl(rt) {
      let base = this.url.endsWith("/") ? this.url : this.url + "/";
      if (rt.counter_version === 51 && !base.endsWith("r51/")) {
        base += "r51/";
      }
      const searchParams = new URLSearchParams({
        customer_id: this.customerId,
        begin_date: this.debugMonth,
        end_date: this.debugMonth,
      });
      if (this.requestorId) {
        searchParams.append("requestor_id", this.requestorId);
      }
      if (this.apiKey) {
        searchParams.append("api_key", this.apiKey);
      }
      if (this.platformFilter) {
        searchParams.append("platform", this.platformFilter);
      }
      return `${base}reports/${rt.code.toLowerCase()}?${searchParams.toString()}`;
    },
    applyLastHarvestableMonthDialog({ values }) {
      this.lastHarvestableMonthUpdated = true;
      // there should be should be only one credentials
      this.lastHarvestableMonth = values[0].last_harvestable_month;
      this.showLastHarvestableMonthDialog = false;
    },
    closeEditPlatformDialog() {
      this.showPlatformEditDialog = false;
    },
    fillSelectedReportTypesBasedOnPlatform() {
      this.selectedReportTypes = this.reportTypesFromPlatform.map((e) => e.pk);
      if (this.$refs.selectedReportTypesField) {
        this.$refs.selectedReportTypesField.resetValidation();
      }
    },
    saveAndCloseEditPlatformDialog(data) {
      this.showPlatformEditDialog = false;
      this.platform = data;
      this.credentials.platform = data;
      if (this.useCounterReportsFromPlatform) {
        this.fillSelectedReportTypesBasedOnPlatform();
      }
    },
    toggleAutoUpdateUrl() {
      this.autoUpdateUrl = !this.autoUpdateUrl;
      if (!this.autoUpdateUrl) {
        this.url = "";
        this.guessUrl();
        this.$nextTick(() => {
          this.$refs.urlField.focus();
        });
      } else {
        this.url = this.currentKnowledgebaseUrl;
        // loose focus
        this.$refs.selectedReportTypesField.focus();
      }
    },
    toggleUseCounterReportsFromPlatform() {
      this.useCounterReportsFromPlatform = !this.useCounterReportsFromPlatform;
      if (this.useCounterReportsFromPlatform) {
        this.fillSelectedReportTypesBasedOnPlatform();
      }
    },
  },

  async mounted() {
    try {
      let promises = [this.loadReportTypes()];
      if (!this.credentialsObject) {
        // we need organizations first before all the rest is loaded
        await this.loadOrganizations();
        promises.push(this.loadPlatforms());
        promises.push(this.loadUseCases());
        promises.push(this.loadExistingCredentials());
      }
      await Promise.all(promises);
    } finally {
      this.initializing = false;
    }
  },

  watch: {
    platformsBaseUrl() {
      if (!this.initializing) {
        this.loadPlatforms();
        this.loadUseCases();
      }
    },
    activePlatformId: {
      immediate: true,
      handler() {
        if (!this.credentials) {
          this.guessUrl();
          this.guessPlatformFilter();
        }
        this.loadRegistryData();
        if (this.useCounterReportsFromPlatform) {
          this.fillSelectedReportTypesBasedOnPlatform();
        }
        if (this.$refs.form) {
          this.$refs.form.resetValidation();
        }
      },
    },
    counterVersion() {
      let currentReportTypes = this.allReportTypes
        .filter((item) => item.counter_version === this.counterVersion)
        .map((item) => item.id);
      this.selectedReportTypes = this.selectedReportTypes.filter((item) =>
        currentReportTypes.includes(item),
      );
      if (this.$refs.form) {
        this.$refs.form.resetValidation();
      }
      if (this.$refs.platformField)
        // sometimes platform is fixed and the field is not there
        this.$refs.platformField.validate();
      if (!this.credentials) {
        this.guessUrl();
        this.guessPlatformFilter();
        if (this.reportTypesFromPlatform.length > 0) {
          this.fillSelectedReportTypesBasedOnPlatform();
        }
      }
    },
    platform() {
      // when the platform is changed and the credentials are not saved yet,
      // we want to select the highest COUNTER version for which there are no credentials
      // and some reports are defined.
      if (!this.credentials && this.activePlatform) {
        let counterVersion = null;
        for (let cv of this.unusedCounterVersions) {
          if (
            this.activePlatform.counter_reports_long.some(
              (e) => e.counter_version === cv,
            )
          ) {
            counterVersion = cv;
            break;
          }
        }
        // if no counter version is found, we select the first one from the list
        // of unused counter versions or the first one from the list of allowed
        // counter versions if there are no unused ones.
        this.counterVersion =
          counterVersion ||
          (this.unusedCounterVersions.length > 0
            ? this.unusedCounterVersions[0]
            : this.allowedCounterVersions[0].value);
      }
      this.$refs.counterVersionField.validate();
    },
    url() {
      this.$nextTick(() => {
        if (this.autoUpdateUrl) {
          this.$refs.urlField.validate();
        }
      });
      delete this.errors.url;
    },
    async showTestDialog(modelValue) {
      // on dialog close, we reload the credentials
      if (!modelValue) {
        await this.reloadCredentials();
      }
    },
  },
};
</script>

<style scoped lang="scss">
.subdued-section {
  //border: solid 1px #eeeeee;
  border-radius: 5px;
  background-color: #f5f5f5;
}

:deep(.v-messages__message) {
  line-height: 1.2;
}

:deep(.v-field__append-inner > .v-icon) {
  opacity: 1;
}

.v-chip__content {
  width: 100% !important;
}

.top_alert {
  margin-bottom: 16px;
  font-size: 16px;
}

.platform_select {
  height: 2.75rem;
  margin-top: -11px;
}

:deep(.v-input__append) {
  pointer-events: auto;
  opacity: 1;
}

.edit-platform {
  pointer-events: auto;
  opacity: 1;
}

.calendar_button {
  margin-left: -10px;
}
</style>
