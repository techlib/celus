<i18n lang="yaml" src="@/locales/dialog.yaml"></i18n>
<i18n lang="yaml">
en:
  title:
    edit: Edit platform
    add: Add platform
  texts:
    adding_platform: You are adding a new platform, please make sure not to duplicate and already existing one.
    editing_platform: You are editing an existing platform, please make sure not to duplicate and already existing one.
  form:
    short_name: Short Name
    name: Name
    provider: Provider
    url: Url
    organization: Organization
    hint:
      short_name: Platform short name (e.g. CUP)
      name: Full platform name (e.g. Cambridge University Presss)
      provider: Platfrom provider - who manages the platform
      url: Website of the platform (e.g. https://www.cambridge.org/core/ )
    similar_platform_name: A platform with similar name already exists
  errors:
    invalid_url: Invalid URL
    saving_error: Failed to save the platform.


cs:
  title:
    edit: Editace platformy
    add: Vytvoření platformy
  texts:
    adding_platform: Přidáváte novou platformu, ujistěte se prosím, že nová platforma neduplikuje nějakou existující.
    editing_platform: Měníte existující platformu, ujistěte se prosím, že změněná platforma neduplikuje nějakou existující.
  form:
    short_name: Krátké jméno
    name: Jméno
    provider: Poskytovatel
    url: Url
    organization: Organizace
    hint:
      short_name: Krátké jméno platformy (např. CUP)
      name: Celé jméno platformy (např. Cambridge University Presss)
      provider: Poskytovatel - kdo zajišťuje chod platformy
      url: Webová stránka platformy (např. https://www.cambridge.org/core/ )
    similar_platform_name: Platformy s podobným jménem už existuje
  errors:
    invalid_url: Špatná URL
    saving_error: Nepodařilo se uložit platformu.
</i18n>

<template>
  <v-form v-model="valid" ref="form">
    <v-card>
      <v-card-title v-if="isEdit" class="headline">{{
        $t("title.edit")
      }}</v-card-title>
      <v-card-title v-else class="headline">{{
        $t("title.add")
      }}</v-card-title>
      <v-card-text>
        <v-container fluid class="pb-0">
          <v-row>
            <v-col>
            <p class="font-italic" v-if=isEdit>
              {{ $t('texts.editing_platform') }}
            </p>
            <p class="font-italic" v-else>
              {{ $t('texts.adding_platform') }}
            </p>
            </v-col>
          </v-row>
          <v-row>
            <v-col cols="12" :md="4">
              <v-select
                v-model="organization"
                :items="organizations"
                item-text="name"
                :label="$t('form.organization')"
                return-object
                :disabled="fixedOrganization"
                :rules="[ruleRequired]"
              >
              </v-select>
            </v-col>
          </v-row>
          <v-row>
            <v-col cols="12" :md="6">
              <v-text-field
                v-model="platform.short_name"
                :label="$t('form.short_name')"
                :rules="[ruleRequired]"
                :hint="$t('form.hint.short_name')"
                persistent-hint
              >
              </v-text-field>
            </v-col>
            <v-col cols="12" :md="6">
              <v-text-field
                v-model="platform.name"
                :label="$t('form.name')"
                :rules="[ruleRequired]"
                :hint="$t('form.hint.name')"
                persistent-hint
              >
              </v-text-field>
            </v-col>
          </v-row>
          <v-row>
            <v-col cols="12" :sm="6" v-if="similarPlatforms.length > 0">
              <v-alert
                type="warning"
                dense
                outlined
              >
                {{ $t("form.similar_platform_name") }}:
                <ul>
                    <li v-for="name in similarPlatforms" :key="name"><strong>{{ name }}</strong></li>
                </ul>
              </v-alert>
            </v-col>
          </v-row>
          <v-row>
            <v-col cols="12" :sm="6">
              <v-text-field
                v-model="platform.provider"
                :label="$t('form.provider')"
                :rules="[ruleRequired]"
                :hint="$t('form.hint.provider')"
                persistent-hint
              >
              </v-text-field>
            </v-col>
            <v-col cols="12" sm="9" md="5">
              <v-text-field
                v-model="platform.url"
                :label="$t('form.url')"
                :rules="[
                  ruleUrlValid,
                ]"
                validate-on-blur
                :error-messages="errors.url"
                :hint="$t('form.hint.url')"
                persistent-hint
              >
              </v-text-field>
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
              <v-btn color="secondary" @click="closeDialog()" class="mr-2">
                <v-icon small class="mr-1">fa fa-times</v-icon>
                {{ $t("close") }}
              </v-btn>
              <v-btn color="primary" @click="saveAndClose()" class="mr-2">
                <v-icon small class="mr-1">fa fa-save</v-icon>
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

export default {
  name: "PlatformEditDialog",
  props: {
    platformId: { required: false, type: Number},
  },
  data() {
    return {
      organization: null,
      platform: {
        short_name: "",
        name: "",
        provider: "",
        url: "",
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
    }),
    isEdit() {
      return !!(this.platformId);
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
      return `/api/organization/${this.selectedOrganization.pk}/platform/`;
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
          stringSimilarity.compareTwoStrings(this.platform.short_name.toLowerCase(), platform.name.toLowerCase()) >= SIMILAR_CONST ||
          stringSimilarity.compareTwoStrings(this.platform.name.toLowerCase(), platform.name.toLowerCase()) >= SIMILAR_CONST
        ) {
          res.push(platform.name);
        }
        if (
          stringSimilarity.compareTwoStrings(this.platform.short_name.toLowerCase(), platform.short_name.toLowerCase()) >= SIMILAR_CONST ||
          stringSimilarity.compareTwoStrings(this.platform.name.toLowerCase(), platform.short_name.toLowerCase()) >= SIMILAR_CONST
        ) {
          res.push(platform.short_name);
        }
      }
      return [...new Set(res)];  // unique
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
      };
    },
    async loadOrganizations() {
      try {
        let result = await axios.get("/api/organization/");
        this.organizations = result.data;
      } catch (error) {
        this.showSnackbar({
          content: "Error loading organizations: " + error,
        });
      }
    },
    async loadPlatform() {
      if (this.isEdit) {
        try {
          let result = await axios.get(
            this.platformsBaseUrl + this.platformId + "/"
          );
          this.platform = result.data;
        } catch (error) {
          this.showSnackbar({
            content:
              `Error loading platform id:${this.platformId}: ` + error,
          });
        }
      } else {
        this.clean();
      }
    },
    async loadPlatforms() {
      if (this.platformsBaseUrl) {
        this.platforms = [];
        try {
          let result = await axios.get(this.platformsBaseUrl);
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
            this.apiData
          );
        } else {
          // we create new platform
          response = await axios.post(`/api/organization/${this.organization.pk}/platform/`, this.apiData);
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
      await this.loadPlatform();

      if (this.selectedOrganization.pk == -1) {
        await this.loadOrganizations();
      } else {
        this.organizations = [this.selectedOrganization];
      }

      if (this.platform.source && this.platform.source.organization) {
        this.organization = this.platform.source.organization;
      } else if (this.organizations.length > 0) {
        this.organization = this.organizations[0];
      }

      await this.loadPlatforms();

      if (this.$refs.form) {
        this.$refs.form.resetValidation();
      }
    },
    ruleRequired(value) {
      return !!value || this.$t("required");
    },
    ruleUrlValid() {
      if (!this.platform.url) {
        delete this.errors.url;
        return true;
      }
      const result = validate(
        { website: this.platform.url },
        { website: { url: true } }
      );
      if (result && result.website) {
        return this.$t("errors.invalid_url");
      }
      delete this.errors.url;
      return true;
    },
  },

  mounted() {
    this.init();
  },

  watch: {
    platformsBaseUrl() {
      this.loadPlatforms();
    },
  },
};
</script>
