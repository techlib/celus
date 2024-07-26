<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml" src="@/locales/dialog.yaml"></i18n>
<i18n lang="yaml" src="@/locales/sources.yaml"></i18n>
<i18n lang="yaml" src="@/locales/sushi.yaml"></i18n>
<i18n lang="yaml">
en:
  add_custom_param: Add custom parameter
  add_custom_param_tooltip: Use this to add parameters for which there is no specific field elsewhere.
  test_dialog: Test SUSHI credentials
  all_versions_used: All versions already defined for this organization and platform - to make changes, edit the corresponding record
  save_and_verify: Save & verify
  save_and_verify_tooltip: Saves current version of credentials and displays a dialog allowing harvesting of data for specified period using these credentials. Very useful to <strong>verify credentials and/or manually download data</strong>.
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
  broken_reports_warning: Some active reports have been marked as broken by Celus - they are probably not supported by this platform. Fix it by deactivating them.
  url_hint_no_report: "URL should not contain the '/reports/' part and anything beyond this. For example 'https://example.com/sushi5/reports/tr?customer_id=1' should be cropped to 'https://example.com/sushi5/'"
  url_hint_no_query: "URL should not contain any query parameters, i. e. there should be no '{search}' part"
  invalid_url: Please enter a valid URL
  duplicate: Name must be unique
  active_report_types: Active report types
  error_saving: It was not possible to save the credentials. Please review the entered values.
  unverified_title: Credentials are not verified
  unverified_details: There are no successful harvests using the current version of these credentials.
  unverified_note: Please verify the credentials by performing a harvest. Note that the credentials won't be used for automatic harvesting unless a successful harvest is performed.
  plan_harvest: Plan harvest
  requestor_id_not_required: Requestor ID is not required for this platform
  see_registry_hint: The Registry icon contains tooltip about this field from the COUNTER registry
  ip_authorization_required: According to the COUNTER registry, this platform requires IP authorization. In case you have problems with harvesting, please contact the platform provider with a request to add the following to the list of authorized IPs
  registry_platform_required: According to the COUNTER registry, this platform requires this attribute to be set
  registry_link: Link to the COUNTER registry record for the selected platform
  check_input: Please check the input, some fields do not have valid values
  cannot_edit_duplicated: These credentials conflict with another set of credentials (they have the same organization, platform and COUNTER version). Unless you delete one of the sets, you cannot edit any of them.
  cannot_create_duplicated: Celus does not support multiple sets of credentials for the same organization, platform and COUNTER version.
  multiple_credentials_info_link: To get more information about duplicated credentials, please see {link}.
  this_article: this article
  show_debug: Show debugging information
  sushi_debug_links: SUSHI debugging links
  no_report_selected: No report selected
  last_harvestable_month: Last harvestable month
  last_harvestable_month_tt: |
    If you know that data is not available before a certain date, you can set this date here. Celus will use this information
    and not try to harvest data before this date.
  last_harvestable_month_updated: Information about last harvestable month was successfully updated
  last_harvestable_month_error: It was not possible to update information about last harvestable month
  auto_update_url_text_off: Set URL manually
  auto_update_url_text_on: URL will be set automatically based on platform metadata
  auto_update_url_hint: URL is automatically managed by Celus based on the platform metadata

cs:
  add_custom_param: Přidat vlastní parametr
  add_custom_param_tooltip: Použijte toto tlačítko pro data, pro která nenajdete odpovídající políčko jinde.
  test_dialog: Test přihlašovacích údajů SUSHI
  all_versions_used: Pro tuto platformu a organizaci jsou již všechny verze použity - pro změnu editujte příslušný záznam
  save_and_verify: Uložit a ověřit
  save_and_verify_tooltip:
    Uloží tuto verzi přihlašovacích údajů a zobrazí dialog pro stahování dat za vybrané období. Tato funkce
    je velmi užitečná pro <strong>ověření správnosti přihlašovacích údajů a/nebo manuální stahování dat</strong>.
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
  broken_reports_warning: Některé aktivní reporty Celus označil jako nefunkční - pravděpodobně nejsou na této platformě podporovány. Toto upozornění odstraníte jejich deaktivací.
  url_hint_no_report: "URL by neměla obsahovat část s '/reports/' a cokoliv po ní. Např. 'https://example.com/sushi5/reports/tr?customer_id=1' by mělo být zkráceno na 'https://example.com/sushi5/'"
  url_hint_no_query: "URL nesmí obsahovat query parametry, tedy část '{search}'"
  invalid_url: Prosím zadejte platné URL
  duplicate: Název musí být unikátní
  active_report_types: Aktivní typy reportů
  error_saving: Přihlašovací údaje nebylo možné uložit. Zkontrolujte prosím zadané hodnoty.
  unverified_title: Přihlašovací údaje nejsou ověřeny
  unverified_details: Současná verze těcho přihlašovacích údajů zatím nebyla úspěšně použita pro stažení dat.
  unverified_note: Ověřte prosím platnost přihlašovacích údajů stažením dat. Upozorňujeme, že dokud nebdou přihlašovací údaje ověřeny, nebude u nich probíhat automatické stahování dat.
  plan_harvest: Naplánovat stahování
  requestor_id_not_required: Requestor ID není pro tuto platformu vyžadováno
  see_registry_hint: Ikona registru obsahuje nápovědu pro toto pole z COUNTER registru
  ip_authorization_required: Podle informací z COUNTER registru je pro tuto platformu vyžadována autorizace IP adresy. Pokud narazíte na problémy se sklízením dat, kontaktujte prosím poskytovatele a požádejte o povolení přístupu z následujících adres
  registry_platform_required: Podle informací z COUNTER registru je tato hodnota vyžadována
  registry_link: Odkaz do COUNTER registru pro vybranou platformu
  check_input: Zkontrolujte prosím zadané hodnoty, některá pole nemají platnou hodnotu.
  cannot_edit_duplicated: Tyto přihlašovací údaje kolidují s jinými (stejná organizace, platforma a verze COUNTER). Dokud nebude konflikt vyřešen smazáním konfliktních údajů, nepůjde tyto údaje upravit.
  cannot_create_duplicated: Celus nepodporuje více přihlašovacích údajů pro stejnou organizaci, platformu a verzi COUNTER.
  multiple_credentials_info_link: Více informací o zdvojených přihlašovacích údajích najdete v {link}.
  this_article: tomto článku
  show_debug: Zobrazit debug informace
  sushi_debug_links: Sushi debug odkazy
  no_report_selected: Nebyl vybrán žádný report
  last_harvestable_month: Poslední stáhnutelný měsíc
  last_harvestable_month_tt: |
    Pokud víte, že data nejsou dostupná před určitým datem, můžete toto datum nastavit zde. Celus bude tuto informaci používat a
    nebude se snažit data stáhnout před tímto datem.
  last_harvestable_month_updated: Informace o posledním stáhnutelném měsíci byla úspěšně aktualizována
  last_harvestable_month_error: Informace o posledním stáhnutelném měsíci nebylo možné aktualizovat
  auto_update_url_text_off: Nastavit URL ručně
  auto_update_url_text_on: URL bude nastavena automaticky z metadat platformy
  auto_update_url_hint: URL je automaticky spravována Celusem na základě metadat platformy
</i18n>

<template>
  <v-form v-model="valid" ref="form">
    <v-card>
      <v-card-title class="headline"
        >{{ $t("title.edit_sushi_credentials") }}
        <v-spacer />
        <v-tooltip bottom max-width="600px" v-if="canShowDebugLinks">
          <template #activator="{ on }">
            <v-icon
              small
              color="grey"
              class="mr-2"
              @click="toggleDebug"
              v-on="on"
            >
              {{ showDebug ? "fa-angle-up" : "fa-angle-down" }}
            </v-icon>
          </template>
          <span>{{ $t("show_debug") }}</span>
        </v-tooltip>
      </v-card-title>
      <v-card-text>
        <!-- debug info -->
        <v-sheet v-if="showDebug && canShowDebugLinks" class="text-right mx-2">
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
            <v-icon x-small class="ml-2">fa-external-link-alt</v-icon>
          </v-chip>
          <span v-if="selectedReportTypes.length === 0" class="pl-1">{{
            $t("no_report_selected")
          }}</span>
        </v-sheet>

        <!-- alert about conflicting credentials -->
        <v-alert v-if="conflictingCredentials" type="error" outlined>
          <p v-if="credentials">{{ $t("cannot_edit_duplicated") }}</p>
          <p v-else>{{ $t("cannot_create_duplicated") }}</p>

          <p>
            <i18n path="multiple_credentials_info_link">
              <template v-slot:link>
                <a
                  href="https://support.celus.net/support/solutions/articles/103000063863"
                  target="_blank"
                  >{{ $t("this_article") }}</a
                >
              </template>
            </i18n>
          </p>
        </v-alert>
        <v-alert
          v-else-if="credentials && credentials.broken"
          type="error"
          outlined
        >
          <p class="bold">{{ $t("broken") }}</p>
          <p>{{ $t("broken_unbreak_manually") }}</p>
          <div>
            <v-btn color="error" outlined @click="markFixed()">{{
              $t("mark_fixed")
            }}</v-btn>
          </div>
        </v-alert>
        <v-alert
          v-else-if="credentials && !credentials.verified"
          type="warning"
          outlined
        >
          <p class="bold">{{ $t("unverified_title") }}</p>
          <p>{{ $t("unverified_details") }}</p>
          <p>{{ $t("unverified_note") }}</p>
          <div>
            <v-btn color="warning" outlined @click="showTestDialog = true">{{
              $t("plan_harvest")
            }}</v-btn>
          </div>
        </v-alert>

        <v-container fluid class="pb-0">
          <v-row>
            <v-col cols="12" :md="4">
              <v-tooltip bottom max-width="600px">
                <template #activator="{ on }">
                  <v-text-field
                    v-model="title"
                    :label="$t('title_label')"
                    v-on="on"
                    dense
                    height="2.75rem"
                  ></v-text-field>
                </template>
                {{ $t("title_tooltip") }}
              </v-tooltip>
            </v-col>
            <v-col cols="12" :md="4">
              <v-text-field
                v-if="credentials"
                :value="organization.name"
                :label="$t('organization')"
                disabled
                dense
                height="2.75rem"
              >
              </v-text-field>
              <v-select
                v-else
                v-model="organization"
                :items="organizations"
                item-text="name"
                :label="$t('organization')"
                return-object
                :disabled="organizationSelected"
                :rules="[ruleRequired]"
                dense
                height="2.75rem"
                :menu-props="{ maxHeight: 480 }"
              >
              </v-select>
            </v-col>
            <v-col cols="12" :md="4">
              <span class="d-flex">
                <v-text-field
                  v-if="credentials || fixedPlatform"
                  :value="activePlatformName"
                  :label="$t('platform')"
                  disabled
                  dense
                  height="2.75rem"
                >
                </v-text-field>
                <v-autocomplete
                  v-else
                  v-model="platform"
                  :items="allowedPlatforms"
                  item-text="name"
                  item-value="pk"
                  :label="$t('platform')"
                  return-object
                  :loading="loadingPlatforms"
                  :rules="[ruleRequired, ruleNoConflictingCredentials]"
                  dense
                  height="2.75rem"
                  :menu-props="{ maxHeight: 480 }"
                  ref="platformField"
                >
                  <template v-slot:prepend-item>
                    <AddPlatformButton
                      v-if="
                        allowUserCreatePlatforms &&
                        (!credentials || !credentials.pk)
                      "
                      @update-platforms="preselectCreatedPlatform"
                      :text="true"
                      small
                      color="success"
                      class="pl-1"
                    />
                  </template>
                  <template v-slot:item="{ item }">
                    <ItemBadge
                      inner-class="v-list-item__title"
                      tag="span"
                      :item="item"
                    />
                  </template>
                </v-autocomplete>
                <v-tooltip bottom v-if="platformRegistryLink">
                  <template #activator="{ on }">
                    <span v-on="on" class="align-self-end mb-3 ms-1">
                      <a
                        target="_blank"
                        :href="`${registryUrlBase}platform/${activePlatform.counter_registry_id}/`"
                        style="line-height: 2rem"
                      >
                        <v-icon small color="counterRegistry"
                          >fa-external-link-alt
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
            <v-col cols="12" :sm="counterVersion === 5 ? 4 : 6">
              <v-text-field
                v-model="requestorId"
                :label="$t('labels.requestor_id')"
                :disabled="!activePlatform"
                persistent-hint
                :hint="requestorIdInfo ? $t('see_registry_hint') : ''"
              >
                <template #append v-if="requestorIdInfo">
                  <RegistryIcon :text="requestorIdInfo" />
                </template>
              </v-text-field>
            </v-col>
            <v-col cols="12" :sm="counterVersion === 5 ? 4 : 6">
              <v-text-field
                v-model="customerId"
                :label="$t('labels.customer_id')"
                :rules="[ruleRequired]"
                :disabled="!activePlatform"
                persistent-hint
                :hint="customerIdInfo ? $t('see_registry_hint') : ''"
              >
                <template #append v-if="customerIdInfo">
                  <RegistryIcon :text="customerIdInfo" />
                </template>
              </v-text-field>
            </v-col>

            <v-col v-if="counterVersion === 5" cols="12" :sm="4">
              <v-text-field
                v-model="apiKey"
                :label="$t('labels.api_key')"
                :disabled="!activePlatform"
                :rules="[ruleAPIkey]"
                persistent-hint
                :hint="apiKeyInfo ? $t('see_registry_hint') : ''"
              >
                <template #append>
                  <RegistryIcon v-if="apiKeyInfo" :text="apiKeyInfo" />
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
                  ruleRequired,
                  ruleUrlValid,
                  ruleUrlC5NoReport,
                  ruleUrlC5NoQueryParams,
                ]"
                validate-on-blur
                :error-messages="errors.url"
                :disabled="
                  !activePlatform ||
                  (autoUpdateUrl && !!currentKnowledgebaseUrl)
                "
                @change="urlManuallyEdited = true"
                ref="urlField"
                :hint="
                  currentKnowledgebaseUrl && autoUpdateUrl
                    ? $t('auto_update_url_hint')
                    : ''
                "
                :persistent-hint="currentKnowledgebaseUrl && autoUpdateUrl"
              >
                <template #append-outer v-if="currentKnowledgebaseUrl">
                  <v-tooltip bottom max-width="400">
                    <template v-slot:activator="{ on }">
                      <v-btn
                        v-on="on"
                        color="primary"
                        icon
                        x-small
                        class="mb-1"
                        @click="toggleAutoUpdateUrl"
                      >
                        <v-icon small color="" v-on="on"
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
            <v-col cols="12" md="5">
              <v-autocomplete
                v-model="selectedReportTypes"
                :items="reportTypes"
                :label="$t('active_report_types')"
                chips
                small-chips
                multiple
                item-text="code"
                item-value="id"
                :rules="[ruleAtLeastOne]"
                :loading="loadingReportTypes"
                :disabled="!activePlatform"
                ref="selectedReportTypesField"
              >
                <template #item="{ item }">
                  <v-list-item-content>
                    <SushiReportIndicator
                      :report="item"
                      :broken-fn="isBroken"
                      :knowledgebase-fn="inKnowledgebase"
                      :registry-fn="inRegistry"
                      show-name
                      show-last-harvestable-month
                    />
                  </v-list-item-content>
                </template>
                <template #selection="{ item, attrs, selected }">
                  <v-chip
                    v-bind="attrs"
                    :input-value="selected"
                    small
                    label
                    :color="isBroken(item) ? 'secondary' : 'primary'"
                  >
                    <SushiReportIndicator
                      :report="item"
                      :broken-fn="isBroken"
                      :knowledgebase-fn="inKnowledgebase"
                      :registry-fn="inRegistry"
                      show-last-harvestable-month
                    />
                  </v-chip>
                </template>
                <template v-slot:append-outer>
                  <v-tooltip bottom max-width="600px">
                    <template #activator="{ on }">
                      <v-btn
                        v-on="on"
                        color="primary"
                        @click="showLastHarvestableMonthDialog = true"
                        icon
                        x-small
                        class="mb-1"
                      >
                        <v-icon>far fa-calendar-alt</v-icon>
                      </v-btn>
                    </template>
                    {{ $t("last_harvestable_month_tt") }}
                  </v-tooltip>
                </template>
              </v-autocomplete>
            </v-col>
          </v-row>
          <v-row class="pb-3 mx-0 pt-2">
            <v-col class="pb-4 subdued-section">
              <v-tooltip bottom max-width="600px">
                <template #activator="{ on }">
                  <h4
                    v-on="counterVersion === 4 ? on : null"
                    class="font-weight-light pl-2"
                    v-text="$t('extra_attributes')"
                  ></h4>
                </template>
                {{ $t("extra_attributes_tooltip") }}
              </v-tooltip>
              <v-container fluid class="pa-0 pl-md-8">
                <v-row v-if="counterVersion === 5">
                  <v-col md="5" class="pt-0">
                    <v-text-field
                      v-model="platformFilter"
                      :label="$t('labels.platform_filter')"
                      :disabled="!activePlatform"
                      :rules="[rulePlatform]"
                      persistent-hint
                      class="mb-3 pb-3"
                      @change="platformFilterManuallyEdited = true"
                      :hint="
                        platformAttrRequired
                          ? $t('registry_platform_required')
                          : ''
                      "
                    >
                      <template v-slot:append>
                        <v-tooltip right max-width="400px">
                          <template #activator="{ on }">
                            <v-icon
                              v-on="on"
                              small
                              :color="
                                platformAttrRequired
                                  ? 'counterRegistry'
                                  : 'secondary'
                              "
                              >{{
                                platformAttrRequired
                                  ? "fa-registered"
                                  : "fa-info-circle"
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
                <div v-if="counterVersion === 4">
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
                        :rules="[ruleRequired, ruleExtraNoDuplicateKey]"
                        :disabled="!activePlatform"
                      >
                      </v-text-field>
                    </v-col>
                    <v-col cols="10" sm="6" md="5" class="py-0">
                      <v-text-field
                        v-model="param.value"
                        :label="$t('labels.variable_value')"
                        :rules="[ruleRequired]"
                        :disabled="!activePlatform"
                      >
                      </v-text-field>
                    </v-col>
                    <v-col cols="auto">
                      <v-btn
                        @click="removeExtraParam(index)"
                        icon
                        color="error"
                      >
                        <v-icon>fa-times</v-icon>
                      </v-btn>
                    </v-col>
                  </v-row>
                  <v-row>
                    <v-col cols="12" class="py-0">
                      <v-tooltip bottom>
                        <template #activator="{ on }">
                          <v-btn
                            v-on="on"
                            @click="addExtraParam()"
                            outlined
                            text
                            color="secondary"
                            :disabled="!activePlatform"
                          >
                            <v-icon left x-small>fa-plus</v-icon>
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
              <v-alert type="warning" outlined>
                {{ $t("ip_authorization_required") }}

                <HarvesterIPAddressList />
              </v-alert>
            </v-col>
          </v-row>
          <v-row>
            <v-col v-if="anyBrokenReports">
              <v-alert type="warning" outlined class="mb-0">
                {{ $t("broken_reports_warning") }}
              </v-alert>
            </v-col>
          </v-row>
        </v-container>
      </v-card-text>
      <v-card-actions>
        <v-container fluid mx-2>
          <v-row no-gutters>
            <v-col cols="auto">
              <v-tooltip bottom>
                <template v-slot:activator="{ on }">
                  <span v-on="on">
                    <v-switch
                      v-model="enabled"
                      :label="$t('sushi.enabled')"
                      class="pl-2 my-0"
                      :disabled="!activePlatform"
                    ></v-switch>
                  </span>
                </template>
                <span>{{ $t("sushi.enabled_tooltip") }}</span>
              </v-tooltip>
            </v-col>
            <v-col cols="auto" class="ml-6" v-if="consortialInstall">
              <v-tooltip bottom>
                <template v-slot:activator="{ on }">
                  <span v-on="on">
                    <v-switch
                      v-model="outsideConsortium"
                      :label="$t('outside')"
                      class="pl-2 my-0"
                      :disabled="!userIsManager || !activePlatform"
                    ></v-switch>
                  </span>
                </template>
                <span>
                  {{ $t("outside_tooltip") }}
                  {{ userIsManager ? "" : $t("only_managers_can_change") }}
                </span>
              </v-tooltip>
            </v-col>
            <v-spacer></v-spacer>
            <v-col cols="auto">
              <DeleteSushiCredentialsDataWidget
                v-if="credentials"
                class="mr-8"
                :credentials="credentials"
                :platform="activePlatform"
                @deleted="
                  $emit('deleted', { id: credentials.pk });
                  $emit('input', false);
                "
              />
              <v-btn @click="closeDialog()" class="mr-2">
                <v-icon small class="mr-1">fa fa-times</v-icon>
                {{ $t("close") }}
              </v-btn>
              <v-tooltip bottom max-width="600px">
                <template #activator="{ on }">
                  <v-btn
                    color="warning"
                    @click="saveAndTest()"
                    class="mr-2"
                    v-on="on"
                    :disabled="saving || disableSave"
                    :loading="saving"
                  >
                    <v-icon small class="mr-1">fa fa-play</v-icon>
                    {{ $t("save_and_verify") }}
                  </v-btn>
                </template>
                <span v-html="$t('save_and_verify_tooltip')"></span>
              </v-tooltip>
              <v-btn
                color="primary"
                @click="saveAndClose()"
                class="mr-2"
                :disabled="saving || disableSave"
                :loading="saving"
              >
                <v-icon small class="mr-1">fa fa-save</v-icon>
                {{ $t("save") }}
              </v-btn>
            </v-col>
          </v-row>
        </v-container>
      </v-card-actions>

      <v-dialog v-model="showTestDialog" max-width="1000px">
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
            <v-btn @click="stopTestDialog()">{{ $t("close") }}</v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>

      <v-dialog v-model="showLastHarvestableMonthDialog" max-width="500px">
        <LastHarvestableMonthEntryWidget
          v-model="reportToLastHarvestableMonth"
          :counter-reports-ordered="selectedReportTypeObjs"
          @close="closeLastHarvestableMonthDialog"
          @apply="updateLastHarvestableMonth"
        />
      </v-dialog>
    </v-card>
  </v-form>
</template>

<script>
import axios from "axios";
import { mapActions, mapGetters } from "vuex";
import AddPlatformButton from "@/components/AddPlatformButton";
import SushiReportIndicator from "@/components/sushi/SushiReportIndicator";
import validate from "validate.js";
import { testSushiUrlReport } from "@/libs/sushi-validation";
import HarvestSelectedWidget from "@/components/sushi/HarvestSelectedWidget";
import RegistryIcon from "@/components/sushi/RegistryIcon";
import HarvesterIPAddressList from "@/components/sushi/HarvesterIPAddressList";
import DeleteSushiCredentialsDataWidget from "@/components/sushi/DeleteSushiCredentialsDataWidget";
import LastHarvestableMonthEntryWidget from "@/components/sushi/LastHarvestableMonthEntryWidget.vue";
import ItemBadge from "@/components/util/ItemBadge";

export default {
  name: "SushiCredentialsEditDialog",
  components: {
    LastHarvestableMonthEntryWidget,
    HarvesterIPAddressList,
    RegistryIcon,
    HarvestSelectedWidget,
    SushiReportIndicator,
    AddPlatformButton,
    DeleteSushiCredentialsDataWidget,
    ItemBadge,
  },
  props: {
    credentialsObject: {},
    value: { default: false },
    existingCredentials: { required: false, type: Array },
    fixedPlatform: { required: false, type: Number },
  },
  data() {
    const credentials = this.credentialsObject;
    let extraParams = [];
    let platformFilter = "";
    if (credentials) {
      for (let [key, value] of Object.entries(credentials.extra_params)) {
        if (key === "platform" && credentials.counter_version === 5) {
          platformFilter = value;
        } else {
          extraParams.push({ key: key, value: value });
        }
      }
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
      urlManuallyEdited: false,
      platformFilterManuallyEdited: false,
      httpUsername: credentials ? credentials.http_username : "",
      httpPassword: credentials ? credentials.http_password : "",
      apiKey: credentials ? credentials.api_key : "",
      platformFilter: platformFilter,
      extraParams: extraParams,
      selectedReportTypes: credentials
        ? [...credentials.counter_reports_long.map((item) => item.id)]
        : [],
      showTestDialog: false,
      showLastHarvestableMonthDialog: false,
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
      valid: false,
      saving: false,
      useCasesData: [],
      prefixApiKey: "",
      prefixPlatform: "",
      initializing: true,
      showDebug: false,
      registryUrlBase: "https://registry.countermetrics.org/",
    };
  },
  computed: {
    ...mapGetters({
      selectedOrganization: "selectedOrganization",
      organizationSelected: "organizationSelected",
      userIsManager: "showManagementStuff",
      consortialInstall: "consortialInstall",
      allowUserCreatePlatforms: "allowUserCreatePlatforms",
      debugMonth: "dateRangeCoverageEndText",
      showManagementStuff: "showManagementStuff",
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
          (item) => item.pk === this.fixedPlatform
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
      if (this.counterVersion === 5 && this.platformFilter.trim()) {
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
        data["id"] = this.credentials.pk;
      } else {
        data["platform_id"] = this.platform.pk;
        data["organization_id"] = this.organization.pk;
      }
      return data;
    },
    reportTypes() {
      return this.allReportTypes.filter(
        (item) => item.counter_version === this.counterVersion
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
        (provider) => provider.counter_version === this.counterVersion
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
            e.counter_version === this.counterVersion
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
          (e) => e.organization === this.organization.pk
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
          a.latest < b.latest ? 1 : a.latest > b.latest ? -1 : 0
        );
        return records[0].url;
      }
      return null;
    },
    knowledgebaseReportTypes() {
      if (this.currentKnowledgebase) {
        let providers = this.activePlatform.knowledgebase.providers.filter(
          (provider) => provider.counter_version == this.counterVersion
        );
        if (providers.length > 0) {
          return providers[0].assigned_report_types.map((e) => e.report_type);
        }
      }
      // Fallback to useCases when there is no knowledgebase
      return this.useCaseReportTypes;
    },
    isValid() {
      return this.valid;
    },
    allowedPlatforms() {
      return this.platforms;
    },
    allowedCounterVersions() {
      return [4, 5];
    },
    conflictingCredentials() {
      /*
       * return true if there are credentials with the same organization, platform and counter
       * version - this is not allowed and should be reflected in the UI
       * */
      return this.similarCredentials.length > 0;
    },
    similarCredentials() {
      /*
        list of credentials that have the same organization, platform and counter version
         */
      if (this.existingCredentials) {
        return this.existingCredentials.filter(
          (cred) =>
            cred.organization.pk === this.organization?.pk &&
            this.platform &&
            cred.platform.pk === this.platform?.pk &&
            cred.counter_version === this.counterVersion &&
            (!this.credentials || cred.pk !== this.credentials?.pk)
        );
      }
      return [];
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
    anyBrokenReports() {
      if (this.credentials) {
        return !!this.selectedReportTypes.filter((item) =>
          this.isBroken({ id: item })
        ).length;
      }
      return false;
    },
    urlPlaceholder() {
      switch (this.counterVersion) {
        case 4:
          return "https://sushi.example.com/c4/";
        case 5:
          return "https://sushi.example.com/c5/";
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
    },
    registrySushiService() {
      if (this.activePlatform && this.activePlatform.registry_data) {
        return this.activePlatform.registry_data.sushi_services.find(
          (service) => service.counter_release == this.counterVersion
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
        this.selectedReportTypes.includes(item.id)
      );
    },
    canShowDebugLinks() {
      // Links for C4 sushi are not working properly
      return this.showManagementStuff && this.counterVersion != 4;
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
        item.long_name = item.name ? `${item.code}: ${item.name}` : item.code;
        if (this.credentials) {
          const reportRec = this.credentials.counter_reports_long.find(
            (e) => e.id === item.id
          );
          this.$set(
            item,
            "last_harvestable_month",
            reportRec?.last_harvestable_month
              ? reportRec.last_harvestable_month.slice(0, 7)
              : null
          );
          this.$set(
            item,
            "last_harvestable_month_user_id",
            reportRec?.last_harvestable_month_user_id || null
          );
          this.$set(
            item,
            "last_harvestable_month_attempt_id",
            reportRec?.last_harvestable_month_attempt_id || null
          );
        }
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
              this.platformsBaseUrl + this.fixedPlatform + "/"
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
              a.name ? a.name.localeCompare(b.name) : -1
            );
            if (this.platform) {
              const machingPlatform = this.platforms.find(
                (item) => item.pk === this.platform.pk
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
      this.$emit("input", false);
    },
    async saveData() {
      this.errors = {};
      this.saving = true;
      try {
        let response = null;
        if (this.credentials) {
          // we have existing credentials - we patch it
          response = await axios.patch(
            `/api/sushi-credentials/${this.credentials.pk}/`,
            this.apiData
          );
        } else {
          // we create new credentials
          response = await axios.post(`/api/sushi-credentials/`, this.apiData);
        }
        this.savedCredentials = response.data;
        await this.showSnackbar({
          content: "Successfully saved SUSHI credentials",
          color: "success",
        });
        this.$emit("update-credentials", response.data);
        await this.saveLastHarvestableMonths();
        return response.data;
      } catch (error) {
        this.showSnackbar({
          content: this.$t("error_saving"),
          color: "error",
        });
        if (error.response != null) {
          this.processErrors(error.response.data);
        }
        return null;
      } finally {
        this.saving = false;
      }
    },
    async saveLastHarvestableMonths() {
      const data = this.selectedReportTypeObjs.map((e) => ({
        credentials_id: this.credentials.pk,
        counter_report_id: e.id,
        last_harvestable_month: e.last_harvestable_month
          ? `${e.last_harvestable_month}-01`
          : null,
      }));
      try {
        await axios.post(
          "/api/sushi-credentials/update-assigned-counter-reports/",
          data
        );
      } catch (error) {
        await this.showSnackbar({
          content: this.$t("last_harvestable_month_error"),
          color: "error",
        });
      }
      await this.reloadCredentials();
    },
    async deleteObject() {
      if (this.credentials) {
        const res = await this.$confirm(this.$t("really_delete"), {
          title: this.$t("confirm_delete"),
          buttonTrueText: this.$t("delete"),
          buttonFalseText: this.$t("cancel"),
        });
        if (res) {
          try {
            await axios.delete(
              `/api/sushi-credentials/${this.credentials.pk}/`
            );
            this.$emit("deleted", { id: this.credentials.pk });
            this.$emit("input", false);
            this.showSnackbar({
              content: this.$t("delete_success"),
              color: "success",
            });
          } catch (error) {
            this.showSnackbar({
              content: "Error deleting SUSHI credentials: " + error,
              color: "error",
            });
          }
        }
      }
    },
    async markFixed() {
      if (this.credentials) {
        try {
          let response = await axios.post(
            `/api/sushi-credentials/${this.credentials.pk}/unset-broken/`
          );
          this.showSnackbar({
            content: this.$t("mark_fixed_success"),
            color: "success",
          });
          this.$emit("update-credentials", response.data);
        } catch (error) {
          this.showSnackbar({
            content: "Error marking SUSHI credentials as fixed: " + error,
            color: "error",
          });
        }
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
            this.$emit("input", false);
          } else {
            let text = `${this.$t("unverified_details")}<br /><br />${this.$t(
              "unverified_note"
            )}`;
            const res = await this.$confirm(text, {
              title: this.$t("unverified_title"),
              buttonTrueText: this.$t("plan_harvest"),
              buttonFalseText: this.$t("close"),
              width: 450,
            });
            if (res) {
              this.showTestDialog = true;
            } else {
              this.$emit("input", false);
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
    async saveAndTest() {
      this.$refs.form.validate();
      if (this.isValid) {
        let data = await this.saveData();
        if (data) {
          if (this.$refs.testWidget) {
            this.$refs.testWidget.clean();
          }
          this.showTestDialog = true;
        }
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
            item.counter_release == this.counterVersion &&
            item.report_id == report.code
        );
      }
      return false;
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
    ruleAPIkey(value) {
      let pattern = /api_?key[:=]/i;
      let isMatch = pattern.test(value);
      if (isMatch) {
        this.prefixApiKey = pattern.exec(value)[0];
      } else {
        this.prefixApiKey = "";
      }
      return (
        !isMatch ||
        `Please remove the "${this.prefixApiKey}" part of your input.`
      );
    },
    rulePlatform(value) {
      let pattern = /platform[:=]/i;
      let isMatch = pattern.test(value);
      if (isMatch) {
        this.prefixPlatform = pattern.exec(value)[0];
      } else {
        this.prefixPlatform = "";
      }
      return (
        !isMatch ||
        `Please remove the "${this.prefixPlatform}" part of your input.`
      );
    },
    ruleRequired(value) {
      return !!value || this.$t("required");
    },
    ruleAtLeastOne(value) {
      return value.length > 0 || this.$t("required");
    },
    ruleExtraNoDuplicateKey(value) {
      return (
        this.extraParams.filter((item) => item.key.trim() === value.trim())
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
      if (this.counterVersion == "5" && !testSushiUrlReport(this.url))
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
        { website: { url: { allowLocal: true } } }
      );
      if (result && result.website) {
        return this.$t("invalid_url");
      }
      return true;
    },
    async reloadCredentials() {
      try {
        let response = await axios.get(
          `/api/sushi-credentials/${this.credentials.pk}/`
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
            this.$set(this.activePlatform, "registry_data", resp.data);
          }
        } catch (error) {
          this.showSnackbar({
            content: "Could not load data from the COUNTER registry",
            color: "warning",
          });
        }
      }
    },
    toggleDebug() {
      this.showDebug = !this.showDebug;
    },
    sushiUrl(rt) {
      const base = this.url.endsWith("/") ? this.url : this.url + "/";
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
      return `${base}reports/${rt.code}/?${searchParams.toString()}`;
    },
    async closeLastHarvestableMonthDialog() {
      this.showLastHarvestableMonthDialog = false;
    },
    updateLastHarvestableMonth(data) {
      Object.entries(data).forEach(([key, value]) => {
        // we want == here because key may be a string and id is an int
        const report = this.allReportTypes.find((e) => e.id == key);
        if (report) {
          this.$set(report, "last_harvestable_month", value);
        }
      });
      this.showLastHarvestableMonthDialog = false;
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
        // lose focus
        this.$refs.selectedReportTypesField.focus();
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
      },
    },
    counterVersion() {
      let currentReportTypes = this.allReportTypes
        .filter((item) => item.counter_version === this.counterVersion)
        .map((item) => item.id);
      this.selectedReportTypes = this.selectedReportTypes.filter((item) =>
        currentReportTypes.includes(item)
      );
      this.$refs.platformField.validate();
      if (!this.credentials) {
        this.guessUrl();
        this.guessPlatformFilter();
      }
    },
    platform() {
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
    async showTestDialog(value) {
      // on dialog close, we reload the credentials
      if (!value) {
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
</style>
