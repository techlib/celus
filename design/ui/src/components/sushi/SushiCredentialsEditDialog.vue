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
  title_in_conflict: <strong>Use a different title</strong>. When creating more than one set of credentials for the same organization, platform and COUNTER version, you need to use distinct titles in order to distinguish between the sets.
  title_in_conflict_hint: Unique title is required
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
  title_in_conflict: <strong>Použijte jiný název</strong>. Pokud vytváříte více přihlašovacích údajů pro stejnout organizaci, platformu a verzi COUNTER, musíte použít různé názvy, aby bylo možné přihlašovací údaje rozlišit.
  title_in_conflict_hint: Je vyžadován unikátní název
  extra_attributes: Extra atributy - vyplňte pouze pokud to poskytovatel vyžaduje
  extra_attributes_tooltip: Tato sekce je určena pro parametry, které jsou používány pouze některými poskytovateli. Pokud přihlašovací údaje, které jste obdrželi od poskytovatele obsahují údaje, pro které není ve formuláři výše položka, můžete je vyplnit zde.
  platform_filter_tooltip: Toto pole je používáno jen některými poskytovateli. Pokud přihlašovací údaje, které jste obdrželi obsahují filtr "platform", můžete jej vyplnit zde.
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
</i18n>

<template>
  <v-form v-model="valid" ref="form">
    <v-card>
      <v-card-title class="headline">{{
        $t("title.edit_sushi_credentials")
      }}</v-card-title>
      <v-card-text>
        <v-alert v-if="credentials && credentials.broken" type="error" outlined>
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
                    :rules="[ruleNoConflictingCredentials]"
                    dense
                    height="2.75rem"
                  >
                    <template v-slot:append v-if="titleHint">
                      <v-tooltip bottom v-if="titleHint">
                        <template #activator="{ on }">
                          <v-icon v-on="on" small color="warning"
                            >fa-exclamation-triangle</v-icon
                          >
                        </template>
                        <div v-html="titleHint" style="max-width: 400px"></div>
                      </v-tooltip>
                    </template>
                  </v-text-field>
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
                :label="$t('platform')"
                return-object
                :loading="loadingPlatforms"
                :rules="[ruleRequired]"
                dense
                height="2.75rem"
                :menu-props="{ maxHeight: 480 }"
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
                  <v-tooltip bottom max-width="600px" v-if="badge(item)">
                    <template #activator="{ on }">
                      <span class="v-list-item__title">{{ item.name }}</span>
                      <v-badge
                        inline
                        :content="$t(badge(item).content)"
                        :color="badge(item).color"
                      >
                        <template v-slot:badge>
                          <span v-on="on">{{ $t(badge(item).content) }}</span>
                        </template>
                      </v-badge>
                    </template>
                    <span>{{ $t(badge(item).tooltip) }}</span>
                  </v-tooltip>
                  <span v-else class="v-list-item__title">
                    {{ item.name }}
                  </span>
                </template>
              </v-autocomplete>
            </v-col>
          </v-row>

          <v-row>
            <v-col cols="12" :sm="counterVersion === 5 ? 4 : 6">
              <v-text-field
                v-model="requestorId"
                :label="$t('labels.requestor_id')"
                :disabled="!activePlatform"
              >
              </v-text-field>
            </v-col>
            <v-col cols="12" :sm="counterVersion === 5 ? 4 : 6">
              <v-text-field
                v-model="customerId"
                :label="$t('labels.customer_id')"
                :rules="[ruleRequired]"
                :disabled="!activePlatform"
              >
              </v-text-field>
            </v-col>

            <v-col v-if="counterVersion === 5" cols="12" :sm="4">
              <v-text-field
                v-model="apiKey"
                :label="$t('labels.api_key')"
                :disabled="!activePlatform"
                :rules="[ruleAPIkey]"
              >
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
                :disabled="!activePlatform"
                @change="urlManuallyEdited = true"
              >
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
              >
                <template #item="{ item }">
                  <v-list-item-content>
                    <SushiReportIndicator
                      :report="item"
                      :broken-fn="isBroken"
                      :knowledgebase-fn="inKnowledgebase"
                      show-name
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
                    />
                  </v-chip>
                </template>
              </v-autocomplete>
            </v-col>
          </v-row>

          <v-row class="pb-3 mx-0 pt-2">
            <v-col class="pb-4 subdued-section" cols="12">
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
                  <v-col md="5" class="py-0">
                    <v-text-field
                      v-model="platformFilter"
                      :label="$t('labels.platform_filter')"
                      :disabled="!activePlatform"
                      :rules="[rulePlatform]"
                    >
                      <template v-slot:append>
                        <v-tooltip right>
                          <template #activator="{ on }">
                            <v-icon v-on="on" small color="secondary"
                              >fa-info-circle</v-icon
                            >
                          </template>
                          <div
                            v-html="$t('platform_filter_tooltip')"
                            style="max-width: 400px"
                          ></div>
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
              <v-btn
                v-if="credentials"
                color="error"
                @click="deleteObject()"
                class="mr-8"
              >
                <v-icon small class="mr-1">fa fa-trash-alt</v-icon>
                {{ $t("delete") }}
              </v-btn>
              <v-btn color="secondary" @click="closeDialog()" class="mr-2">
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
                    :disabled="saving"
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
                :disabled="saving"
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
            <v-btn color="secondary" @click="stopTestDialog()">{{
              $t("close")
            }}</v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>
    </v-card>
  </v-form>
</template>

<script>
import axios from "axios";
import { isEqual } from "lodash";
import { mapActions, mapGetters } from "vuex";
import { badge } from "@/libs/sources.js";
import AddPlatformButton from "@/components/AddPlatformButton";
import SushiReportIndicator from "@/components/sushi/SushiReportIndicator";
import validate from "validate.js";
import { testSushiUrlReport } from "@/libs/sushi-validation";
import HarvestSelectedWidget from "@/components/sushi/HarvestSelectedWidget";

export default {
  name: "SushiCredentialsEditDialog",
  components: {
    HarvestSelectedWidget,
    SushiReportIndicator,
    AddPlatformButton,
  },
  props: {
    credentialsObject: {},
    value: { default: false },
    existingCredentials: { required: false, type: Array },
    fixedPlatform: { required: false, type: Number },
  },
  data() {
    return {
      allReportTypes: [],
      organizationId: null,
      organization: "",
      platformId: null,
      platform: "",
      requestorId: "",
      customerId: "",
      counterVersion: 5,
      url: "",
      urlManuallyEdited: false,
      httpUsername: "",
      httpPassword: "",
      apiKey: "",
      platformFilter: "",
      extraParams: [],
      selectedReportTypes: [],
      showTestDialog: false,
      organizations: [],
      platforms: [],
      errors: {},
      savedCredentials: null,
      enabled: true,
      outsideConsortium: true,
      title: "",
      loadingPlatforms: false,
      loadingReportTypes: false,
      valid: false,
      saving: false,
      useCasesData: [],
      prefixApiKey: "",
      prefixPlatform: "",
    };
  },
  computed: {
    ...mapGetters({
      selectedOrganization: "selectedOrganization",
      organizationSelected: "organizationSelected",
      userIsManager: "showManagementStuff",
      consortialInstall: "consortialInstall",
      allowUserCreatePlatforms: "allowUserCreatePlatforms",
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
        return this.fixedPlatform;
      }
      return this.platform;
    },
    apiData() {
      let extraParams = {};
      for (let rec of this.extraParams) {
        if (rec.key.trim()) extraParams[rec.key] = rec.value;
      }
      if (this.counterVersion === 5) {
        extraParams.platform = this.platformFilter;
      }
      let data = {
        title: this.title,
        customer_id: this.customerId,
        requestor_id: this.requestorId,
        api_key: this.apiKey,
        url: this.url,
        counter_version: this.counterVersion,
        http_username: this.httpUsername,
        http_password: this.httpPassword,
        extra_params: extraParams,
        counter_reports: this.selectedReportTypes,
        enabled: this.enabled,
        outside_consortium: this.outsideConsortium,
      };
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
      return this.platforms.sort((a, b) =>
        a.name ? a.name.localeCompare(b.name) : -1
      );
    },
    allowedCounterVersions() {
      return [4, 5];
    },
    conflictingCredentials() {
      /*
       * return true if there are credentials with the same organization, platform and counter
       * version and also the same name - this is not allowed and should be reflected in the
       * UI
       * */
      return !!this.similarCredentials.filter(
        (cred) => cred.title == this.title
      ).length;
    },
    similarCredentials() {
      /*
        list of credentials that have the same organization, platform and counter version
         */
      if (this.existingCredentials) {
        return this.existingCredentials.filter(
          (cred) =>
            cred.organization.pk === this.organization.pk &&
            this.platform &&
            cred.platform.pk === this.platform.pk &&
            cred.counter_version === this.counterVersion &&
            (!this.credentials || cred.pk !== this.credentials.pk)
        );
      }
      return [];
    },
    titleHint() {
      if (this.conflictingCredentials) {
        return this.$t("title_in_conflict");
      }
      return false;
    },
    platformsBaseUrl() {
      if (this.organization && this.organization.pk) {
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
      return this.activePlatform.name || this.activePlatform.short_name;
    },
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    credentialsPropToData() {
      let credentials = this.credentials;
      if (!credentials) {
        // no credentials - we init to the initial state
        this.title = "";
        this.organizationId = null;
        this.organization = { name: "" };
        this.platformId = null;
        this.platform = { name: "" };
        this.requestorId = "";
        this.customerId = "";
        this.counterVersion = 5;
        this.url = "";
        this.httpUsername = "";
        this.httpPassword = "";
        this.apiKey = "";
        this.extraParams = [];
        this.selectedReportTypes = [];
        this.errors = {};
        this.savedCredentials = null;
        this.enabled = true;
        this.outsideConsortium = true;
      } else {
        let extraParams = [];
        for (let [key, value] of Object.entries(credentials.extra_params)) {
          if (key === "platform") {
            this.platformFilter = value;
          }
          extraParams.push({ key: key, value: value });
        }
        this.title = credentials.title;
        this.organizationId = credentials.organization.id;
        this.organization = credentials.organization;
        this.platformId = credentials.platform.id;
        this.platform = credentials.platform;
        this.requestorId = credentials.requestor_id;
        this.customerId = credentials.customer_id;
        this.counterVersion = credentials.counter_version;
        this.url = credentials.url;
        this.httpUsername = credentials.http_username;
        this.httpPassword = credentials.http_password;
        this.apiKey = credentials.api_key;
        this.extraParams = extraParams;
        this.selectedReportTypes = [
          ...credentials.counter_reports_long.map((item) => item.id),
        ];
        this.enabled = credentials.enabled;
        this.outsideConsortium = credentials.outside_consortium;
      }
    },
    async loadReportTypes() {
      this.loadingReportTypes = true;
      try {
        let result = await axios.get("/api/counter-report-type/");
        this.allReportTypes = result.data;
        this.allReportTypes.forEach(
          (item) =>
            (item.long_name = item.name
              ? `${item.code}: ${item.name}`
              : item.code)
        );
      } catch (error) {
        this.showSnackbar({ content: "Error loading report types: " + error });
      } finally {
        this.loadingReportTypes = false;
      }
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
            if (this.platform) {
              const machingPlatforms = this.platforms.filter(
                (item) => item.pk === this.platform.pk
              );
              if (machingPlatforms) {
                this.platform = machingPlatforms[0];
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
        this.showSnackbar({
          content: "Successfully saved SUSHI credentials",
          color: "success",
        });
        this.$emit("update-credentials", response.data);
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
      this.$refs.form.validate();
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
      this.$emit("set-dirty");
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
    async init() {
      this.savedCredentials = null;
      this.credentialsPropToData();
      if (!this.credentials) {
        await this.loadOrganizations();
        await this.loadPlatforms();
        await this.loadUseCases();
      }
      if (this.$refs.form) {
        this.$refs.form.resetValidation();
      }
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
        let providers = this.currentKnowledgebase.providers.filter(
          (provider) => provider.counter_version == this.counterVersion
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
        return this.$t("title_in_conflict_hint");
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
        { website: { url: true } }
      );
      if (result && result.website) {
        return this.$t("invalid_url");
      }
      return true;
    },
    badge(item) {
      return badge(item);
    },
  },

  async mounted() {
    await this.loadReportTypes();
    await this.init();
  },

  watch: {
    credentialsObject(value) {
      if (value) {
        this.init();
      }
    },
    value(value) {
      if (value === true) this.init();
    },
    platformsBaseUrl() {
      this.loadPlatforms();
    },
    activePlatform() {
      if (!this.credentials) {
        this.guessUrl();
      }
    },
    counterVersion() {
      let currentReportTypes = this.allReportTypes
        .filter((item) => item.counter_version === this.counterVersion)
        .map((item) => item.id);
      this.selectedReportTypes = this.selectedReportTypes.filter((item) =>
        currentReportTypes.includes(item)
      );
      if (!this.credentials) {
        this.guessUrl();
      }
    },
    url() {
      delete this.errors.url;
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
