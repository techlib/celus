<i18n lang="yaml" src="@/locales/dialog.yaml"></i18n>
<i18n lang="yaml" src="@/locales/sushi.yaml"></i18n>

<i18n lang="yaml">
en:
  title:
    edit: Edit platform
    add: Add platform
  texts:
    adding_platform: You are adding a new platform, please make sure not to duplicate an already existing one.
    editing_platform: You are editing an existing platform, please make sure not to duplicate an already existing one.
    counter_report_from_knowledgebase_on: COUNTER reports will be used based on the knowledgebase of the platform.
    counter_report_from_knowledgebase_off: Fill in COUNTER reports manually.
  form:
    short_name: Short Name
    name: Name
    provider: Provider / Vendor
    url: URL
    organization: Organization
    hint:
      short_name: Platform short name (e.g. CUP)
      name: Full platform name (e.g. Cambridge University)
      provider: Platfrom provider (vendor) - who manages the platform
      url: "Website of the platform (e.g. https://www.cambridge.org/core/). Note that this URL is not SUSHI URL."
      counter_report_knowledgebase: Report Types are automatically managed by CELUS based on the platform's knowledgebase
    similar_platform_name: A platform with similar name already exists
    counter_report_types: COUNTER Report types
  errors:
    invalid_url: "Invalid URL (valid URL starts with 'http(s)://', e.g. 'https://www.cambridge.org/core')"
    short_name_not_unique: "Short name is not unique"
    saving_error: Failed to save the platform.

cs:
  title:
    edit: Editace platformy
    add: Vytvoření platformy
  texts:
    adding_platform: Přidáváte novou platformu, ujistěte se prosím, že nová platforma neduplikuje nějakou existující.
    editing_platform: Měníte existující platformu, ujistěte se prosím, že změněná platforma neduplikuje nějakou existující.
    counter_report_from_knowledgebase_on: COUNTER reporty budou použity na základě znalostní databáze o platformě.
    counter_report_from_knowledgebase_off: Vyplnit COUNTER reporty ručně.
  form:
    short_name: Krátké jméno
    name: Jméno
    provider: Poskytovatel / Provozovatel
    url: URL
    organization: Organizace
    hint:
      short_name: Krátké jméno platformy (např. CUP)
      name: Celé jméno platformy (např. Cambridge University)
      provider: Poskytovatel (provozovatel) - kdo zajišťuje chod platformy
      url: "Webová stránka platformy (např. https://www.cambridge.org/core/). Pozn: tato URL není URL pro SUSHI."
      counter_report_knowledgebase: Typy reportů budou automaticky spravovány CELUSem na základě znalostní databáze platformy
    similar_platform_name: Platforma s podobným jménem už existuje
    counter_report_types: Typy COUNTER reportů
  errors:
    invalid_url: "Neplatná URL (platná URL začíná na 'http(s)://', např. 'https://www.cambridge.org/core')"
    short_name_not_unique: "Krátké jméno není unikátní"
    saving_error: Nepodařilo se uložit platformu.
</i18n>

<template>
  <v-form v-model="valid" ref="form">
    <v-card>
      <v-card-title v-if="isEdit" class="headline">{{
        $t("title.edit")
      }}</v-card-title>
      <v-card-title v-else class="headline">{{ $t("title.add") }}</v-card-title>
      <v-card-text>
        <v-container fluid class="pb-0">
          <v-row v-if="(isEdit && editableDetails) || !isEdit">
            <v-col>
              <p class="font-italic" v-if="isEdit">
                {{ $t("texts.editing_platform") }}
              </p>
              <p class="font-italic" v-else>
                {{ $t("texts.adding_platform") }}
              </p>
            </v-col>
          </v-row>
          <v-row>
            <v-col cols="12" :md="4" v-if="showOrganizationSelect">
              <v-select
                v-model="organization"
                :items="organizations"
                item-title="name"
                :label="$t('form.organization')"
                return-object
                :disabled="fixedOrganization"
                :rules="[rules.required]"
              >
              </v-select>
            </v-col>
          </v-row>
          <v-row>
            <v-col cols="12" :md="6">
              <v-text-field
                v-model="platform.short_name"
                :label="$t('form.short_name')"
                :rules="[rules.required, ruleUniqueShortName]"
                :hint="$t('form.hint.short_name')"
                :disabled="!editableDetails"
                persistent-hint
              >
              </v-text-field>
            </v-col>
            <v-col cols="12" :md="6">
              <v-text-field
                v-model="platform.name"
                :label="$t('form.name')"
                :rules="[rules.required]"
                :hint="$t('form.hint.name')"
                :disabled="!editableDetails"
                persistent-hint
              >
              </v-text-field>
            </v-col>
          </v-row>
          <v-row v-if="editableDetails">
            <v-col cols="12" :sm="6" v-if="similarPlatforms.length > 0">
              <v-alert type="warning" density="compact" variant="outlined">
                {{ $t("form.similar_platform_name") }}:
                <ul>
                  <li v-for="name in similarPlatforms" :key="name">
                    <strong>{{ name }}</strong>
                  </li>
                </ul>
              </v-alert>
            </v-col>
          </v-row>
          <v-row>
            <v-col cols="12" :sm="6">
              <v-text-field
                v-model="platform.provider"
                :label="$t('form.provider')"
                :rules="[rules.required]"
                :hint="$t('form.hint.provider')"
                :disabled="!editableDetails"
                persistent-hint
              >
              </v-text-field>
            </v-col>
            <v-col cols="12" sm="9" md="5">
              <v-text-field
                v-model="platform.url"
                :label="$t('form.url')"
                :rules="[ruleUrlValid]"
                validate-on-blur
                :error-messages="errors.url"
                :hint="$t('form.hint.url')"
                persistent-hint
                :disabled="!editableDetails"
              >
              </v-text-field>
            </v-col>
          </v-row>
          <v-row>
            <v-col cols="12" class="active_report">
              <v-autocomplete
                v-if="counterReports"
                density="comfortable"
                v-model="selectedCounterReports"
                :items="counterReportsSorted"
                :label="$t('form.counter_report_types')"
                multiple
                item-title="code"
                item-value="id"
                :loading="loadingCounterReports"
                :disabled="!manuallyUpdateCounterReports"
                ref="selectedReportTypesField"
                :hint="
                  !manuallyUpdateCounterReports
                    ? $t('form.hint.counter_report_knowledgebase')
                    : ''
                "
                :persistent-hint="!manuallyUpdateCounterReports"
              >
                <template #item="{ props, item }">
                  <v-list-item
                    v-bind="props"
                    title
                    v-if="!isBlacklisted(item.raw)"
                  >
                    <template v-slot:default>
                      <SushiReportIndicator
                        v-if="item.raw.code"
                        :report="item.raw"
                        show-name
                      ></SushiReportIndicator>
                    </template>
                  </v-list-item>
                  <v-tooltip location="bottom" max-width="400" v-else>
                    <template #activator="{ props }">
                      <span v-bind="props">
                        <v-list-item title disabled>
                          <SushiReportIndicator
                            :report="item.raw"
                            :blacklisted-fn="isBlacklisted"
                            show-name
                          ></SushiReportIndicator>
                        </v-list-item>
                      </span>
                    </template>
                    <i18n-t
                      keypath="sushi.blacklisted_report_type_desc"
                      tag="span"
                    >
                      <template #link>
                        <a
                          :href="`mailto:${contactEmail}`"
                          class="text-warning"
                          target="_blank"
                          >{{ contactEmail }}</a
                        >
                      </template>
                    </i18n-t>
                  </v-tooltip>
                </template>
                <template #selection="{ item, props, selected }">
                  <v-chip
                    v-bind="props"
                    :model-value="selected"
                    size="small"
                    label
                    variant="flat"
                    color="primary"
                  >
                    <SushiReportIndicator
                      v-if="item.raw.code"
                      :report="item.raw"
                      is-autocomplete
                      show-version
                    ></SushiReportIndicator>
                  </v-chip>
                </template>
                <template #append>
                  <v-tooltip location="bottom" max-width="400">
                    <template
                      v-slot:activator="{ props }"
                      v-if="canUsePlatformsFromKnowledgebase"
                    >
                      <v-btn
                        color="primary"
                        variant="plain"
                        icon
                        @click="toggleUseCounterReportsFromKnowledgebase"
                        size="small"
                        v-bind="props"
                      >
                        <v-icon size="small"
                          >fa
                          {{
                            !manuallyUpdateCounterReports
                              ? "fa-edit"
                              : "fa-book"
                          }}</v-icon
                        >
                      </v-btn>
                    </template>
                    <span
                      >{{
                        !manuallyUpdateCounterReports
                          ? $t("texts.counter_report_from_knowledgebase_off")
                          : $t("texts.counter_report_from_knowledgebase_on")
                      }}
                    </span>
                  </v-tooltip>
                </template>
              </v-autocomplete>
            </v-col>
          </v-row>
        </v-container>
      </v-card-text>
      <v-card-actions>
        <v-container fluid mx-2>
          <v-row no-gutters>
            <v-col>
              <v-spacer></v-spacer>
            </v-col>
            <v-col cols="auto">
              <v-btn
                @click="closeDialog"
                class="mr-2"
                color="defaultButton"
                variant="elevated"
              >
                <v-icon size="small" class="mr-2">fa fa-times</v-icon>
                {{ $t("close") }}
              </v-btn>
              <v-btn
                color="primary"
                @click="saveAndClose"
                class="mr-2"
                variant="elevated"
                :disabled="!isValid"
              >
                <v-icon size="small" class="mr-2">fa fa-save</v-icon>
                {{ $t("save") }}
              </v-btn>
            </v-col>
          </v-row>
        </v-container>
      </v-card-actions>
    </v-card>
  </v-form>
</template>

<script>
import axios from "axios";
import { mapActions, mapGetters } from "vuex";
import validate from "validate.js";
import stringSimilarity from "string-similarity";
import formRulesMixin from "@/mixins/formRulesMixin";
import SushiReportIndicator from "@/components/sushi/SushiReportIndicator";

export default {
  name: "PlatformEditDialog",

  mixins: [formRulesMixin],
  components: {
    SushiReportIndicator,
  },

  props: {
    platformId: { required: false, type: Number },
  },
  data() {
    return {
      counterReports: [],
      selectedCounterReports: [],
      loadingCounterReports: false,
      organization: null,
      platform: {
        short_name: "",
        name: "",
        provider: "",
        url: "",
        counter_reports: [],
        counter_reports_source: "manual",
      },
      organizations: [],
      platforms: [],
      errors: {},
      valid: false,
    };
  },
  computed: {
    ...mapGetters({
      selectedOrganization: "selectedOrganization",
      contactEmail: "contactEmail",
    }),
    isEdit() {
      return !!this.platformId;
    },
    fixedOrganization() {
      return this.selectedOrganization.pk != -1 || this.isEdit;
    },
    apiData() {
      let data = {
        short_name: this.platform.short_name,
        name: this.platform.name,
        provider: this.platform.provider,
        url: this.platform.url,
        counter_reports: this.selectedCounterReports,
        counter_reports_source: this.platform.counter_reports_source,
      };
      if (this.platform) {
        data.pk = this.platform.pk;
      }
      return data;
    },
    isValid() {
      return this.valid;
    },
    platformsBaseUrl() {
      if (this.organization) {
        return `/api/organization/${this.organization.pk}/platform/`;
      }
      return null;
    },
    platformsAllUrl() {
      if (this.organization) {
        return `/api/organization/${this.organization.pk}/all-platform/?public_only=False`;
      }
      return null;
    },
    similarPlatforms() {
      const SIMILAR_CONST = 0.5;
      // search by short name
      let res = [];
      if (this.platform.short_name == "" && this.platform.name == "") {
        return [];
      }
      // compare platforms
      for (const platform of this.platforms) {
        if (platform.pk == this.platform.pk) {
          continue;
        }
        if (
          stringSimilarity.compareTwoStrings(
            this.platform.short_name.toLowerCase(),
            platform.name.toLowerCase(),
          ) >= SIMILAR_CONST ||
          stringSimilarity.compareTwoStrings(
            this.platform.name.toLowerCase(),
            platform.name.toLowerCase(),
          ) >= SIMILAR_CONST
        ) {
          res.push(platform.name);
        }
        if (
          stringSimilarity.compareTwoStrings(
            this.platform.short_name.toLowerCase(),
            platform.short_name.toLowerCase(),
          ) >= SIMILAR_CONST ||
          stringSimilarity.compareTwoStrings(
            this.platform.name.toLowerCase(),
            platform.short_name.toLowerCase(),
          ) >= SIMILAR_CONST
        ) {
          res.push(platform.short_name);
        }
      }
      return [...new Set(res)]; // unique
    },
    manuallyUpdateCounterReports() {
      return this.platform.counter_reports_source == "manual";
    },
    editableDetails() {
      if (this.isEdit) {
        if (this.platform.source) {
          // Only platforms with organization source can be editted
          return !!this.platform.source.organization;
        } else {
          // Not updated externally
          return true;
        }
      } else {
        // Can edit everything for new credentials
        return true;
      }
    },
    showOrganizationSelect() {
      return !this.isEdit || this.platform?.source?.organization;
    },
    counterReportsFromKnowledgebase() {
      let counterReports = [];
      for (const provider of this.platform?.knowledgebase?.providers || []) {
        for (const art of provider.assigned_report_types) {
          counterReports.push(`${provider.counter_version}|${art.report_type}`);
        }
      }
      return this.counterReportsSorted.filter((e) =>
        counterReports.includes(`${e.counter_version}|${e.code}`),
      );
    },
    counterReportsSorted() {
      return this.sortCounterReports(this.counterReports);
    },
    canUsePlatformsFromKnowledgebase() {
      return !!this.platform.knowledgebase;
    },
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    clean() {
      this.platform = {
        short_name: "",
        name: "",
        provider: "",
        url: "",
        counter_reports: [],
        counter_reports_source: this.isEdit ? "knowledgebase" : "manual",
      };
    },
    async loadOrganizations() {
      try {
        let result = await axios.get("/api/organization/");
        this.organizations = result.data;
        if (this.$store.getters.showManagementStuff) {
          this.organizations.unshift({
            name: "All",
            name_cs: "Všechny",
            name_en: "All",
            pk: -1,
            extra: true,
          });
        }
      } catch (error) {
        this.showSnackbar({
          content: "Error loading organizations: " + error,
        });
      }
    },
    async loadPlatform() {
      if (this.isEdit && this.platformsBaseUrl) {
        try {
          let result = await axios.get(
            this.platformsBaseUrl + this.platformId + "/",
          );
          this.clean();
          this.platform = result.data;
          this.selectedCounterReports = this.sortCounterReports(
            this.platform.counter_reports_long,
          ).map((e) => e.pk);
          if (!this.canUsePlatformsFromKnowledgebase) {
            this.platform.counter_reports_source = "manual";
          }
        } catch (error) {
          this.showSnackbar({
            content: `Error loading platform id:${this.platformId}: ` + error,
            color: "error",
          });
        }
      } else {
        this.clean();
      }
    },
    async loadPlatforms() {
      if (this.platformsAllUrl) {
        this.platforms = [];
        try {
          let result = await axios.get(this.platformsAllUrl);
          this.platforms = result.data;
        } catch (error) {
          this.showSnackbar({ content: "Error loading platforms: " + error });
        }
      }
    },
    closeDialog() {
      this.$emit("close");
    },
    async saveData() {
      this.errors = {};
      try {
        let response = null;
        if (this.isEdit) {
          // we have existing platform
          response = await axios.put(
            `/api/organization/${this.organization.pk}/platform/${this.platform.pk}/`,
            this.apiData,
          );
        } else {
          // we create new platform
          response = await axios.post(
            `/api/organization/${this.organization.pk}/platform/`,
            this.apiData,
          );
        }
        this.showSnackbar({
          content: "Successfully saved Platform",
          color: "success",
        });
        this.$emit("saved", response.data);
        return true;
      } catch (error) {
        this.showSnackbar({
          content: this.$t("errors.saving_error"),
          color: "error",
        });
        if (error.response != null) {
          this.processErrors(error.response.data);
        }
        return false;
      }
    },
    processErrors(errors) {
      this.errors = errors;
    },
    async saveAndClose() {
      this.$refs.form.validate();
      if (this.isValid) {
        await this.saveData();
      }
    },
    async init() {
      // on load the organization is not set yet and `loadPlatform` depends
      // on the organization.pk
      // we use the selected organization as default
      if (!this.organization && this.selectedOrganization) {
        this.organization = this.selectedOrganization;
      }
      await this.loadCounterReports();
      await this.loadPlatform();

      if (this.selectedOrganization.pk === -1) {
        await this.loadOrganizations();
      } else {
        this.organizations = [this.selectedOrganization];
      }

      if (this.platform.source && this.platform.source.organization) {
        this.organization = this.platform.source.organization;
      } else if (this.organizations.length > 0) {
        this.organization = this.organizations[0];
      }

      if (this.$refs.form) {
        this.$refs.form.resetValidation();
      }
    },
    ruleUniqueShortName(value) {
      return (
        !this.platforms.some((e) => e.short_name === value) ||
        this.$t("errors.short_name_not_unique")
      );
    },
    ruleUrlValid() {
      if (!this.platform.url) {
        delete this.errors.url;
        return true;
      }
      const result = validate(
        { website: this.platform.url },
        { website: { url: true } },
      );
      if (result && result.website) {
        return this.$t("errors.invalid_url");
      }
      delete this.errors.url;
      return true;
    },
    async loadCounterReports() {
      this.loadingCounterReports = true;
      try {
        let result = await axios.get("/api/counter-report-type/");
        this.counterReports = result.data;
        this.updateCounterReportsObjects();
      } catch (error) {
        this.showSnackbar({
          content: "Error loading counter reports: " + error,
        });
      } finally {
        this.loadingCounterReports = false;
      }
    },
    updateCounterReportsObjects() {
      this.counterReports.forEach((item) => {
        item.long_name = item.name ? `${item.code}: ${item.name}` : item.code;
        item.pk = item.id;
      });
    },
    toggleUseCounterReportsFromKnowledgebase() {
      if (this.platform) {
        if (this.platform.counter_reports_source == "knowledgebase") {
          this.platform.counter_reports_source = "manual";
          this.$refs.selectedReportTypesField.focus();
        } else {
          this.platform.counter_reports_source = "knowledgebase";
          if (this.counterReportsFromKnowledgebase) {
            this.selectedCounterReports =
              this.counterReportsFromKnowledgebase.map((e) => e.pk);
          }
        }
      }
    },
    sortCounterReports(arr) {
      let reports = [...arr];
      reports.sort((a, b) => {
        if (a.counter_version == b.counter_version) {
          return a.code.localeCompare(b.code);
        } else {
          // reversed
          return b.counter_version - a.counter_version;
        }
      });
      return reports;
    },
    isBlacklisted(report) {
      if (!report.requires_whitelisting) {
        return false;
      }
      if (this.platform.knowledgebase) {
        return !(this.platform.knowledgebase.providers || []).some(
          (e) =>
            e.counter_version == report.counter_version &&
            e.assigned_report_types.some(
              (e) => e.report_type == report.code && e.whitelisted,
            ),
        );
      }
      return true;
    },
  },

  mounted() {
    this.init();
  },

  watch: {
    organization() {
      if (!this.isEdit) {
        // update platforms only when organization can be picked
        this.loadPlatforms();
      }
    },
  },
};
</script>

<style lang="scss" scoped>
p {
  color: rgba(0, 0, 0, 0.6);
}
:deep(.v-input__append) {
  pointer-events: auto;
  opacity: 1;
}
</style>
