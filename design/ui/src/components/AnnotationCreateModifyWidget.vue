<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<i18n lang="yaml" src="@/locales/dialog.yaml"></i18n>

<i18n lang="yaml" src="@/locales/annotations.yaml"></i18n>

<i18n lang="yaml">
en:
  all: All
cs:
  all: Všechny
</i18n>

<template>
  <v-form ref="form" v-model="valid" @submit.prevent="save">
    <v-container fluid>
      <v-row>
        <v-col>
          <v-autocomplete
            v-model="organizationId"
            :items="organizations"
            item-title="name"
            item-value="pk"
            :label="$t('organization')"
          >
            <template v-slot:item="{ item, props }">
              <v-list-item v-bind="props" :class="{ bold: item.raw.extra }">
              </v-list-item>
            </template>
          </v-autocomplete>
        </v-col>
        <v-col>
          <v-autocomplete
            v-model="platformId"
            :items="availablePlatforms"
            item-value="pk"
            item-title="name"
            :loading="loadingPlatforms"
            :disabled="fixPlatform && platform !== null"
            :label="$t('platform')"
          >
            <template v-slot:item="{ item, props }">
              <v-list-item v-bind="props" :class="{ bold: item.raw.extra }">
              </v-list-item>
            </template>
          </v-autocomplete>
        </v-col>
      </v-row>
      <v-row>
        <v-col>
          <v-menu
            v-model="startDateMenu"
            :close-on-content-click="false"
            :nudge-right="40"
            transition="scale-transition"
            offset-y
            min-width="auto"
            color="primary"
          >
            <template v-slot:activator="{ props }">
              <v-text-field
                style="min-width: 200px"
                v-model="formattedStartDateComputed"
                :label="$t('title_fields.start_date')"
                prepend-icon="fa fa-calendar"
                :error-messages="validateDateRange()"
                readonly
                v-bind="props"
              ></v-text-field>
            </template>
            <VueDatePicker
              v-model="startDate"
              :locale="$i18n.locale"
              :enable-time-picker="false"
              inline
              auto-apply
            ></VueDatePicker>
          </v-menu>
        </v-col>
        <v-col>
          <v-menu
            v-model="endDateMenu"
            :close-on-content-click="false"
            :nudge-right="40"
            transition="scale-transition"
            offset-y
            min-width="auto"
            color="primary"
          >
            <template v-slot:activator="{ props }">
              <v-text-field
                style="min-width: 200px"
                v-model="formattedEndDateComputed"
                :label="$t('title_fields.end_date')"
                prepend-icon="fa fa-calendar"
                readonly
                v-bind="props"
              ></v-text-field>
            </template>
            <VueDatePicker
              v-model="endDate"
              :enable-time-picker="false"
              :locale="$i18n.locale"
              inline
              auto-apply
            ></VueDatePicker>
          </v-menu>
        </v-col>
        <v-spacer></v-spacer>
        <v-col cols="auto">
          <v-select
            :items="importanceLevels"
            :label="$t('annotations.labels.level')"
            v-model="level"
            item-title="text"
            style="min-width: 245px"
          >
            <template v-slot:item="{ props, item }">
              <v-list-item v-bind="props">
                <template #prepend>
                  <v-icon size="small" class="mr-2" :color="item.raw.color">{{
                    item.raw.icon
                  }}</v-icon>
                </template>
              </v-list-item>
            </template>
            <template v-slot:selection="{ props, item }">
              <v-icon
                size="small"
                class="mr-2"
                :color="item.raw.color"
                v-bind="props"
                >{{ item.raw.icon }}</v-icon
              >
              {{ item.raw.text }}
            </template>
          </v-select>
        </v-col>
      </v-row>
      <v-row>
        <v-col cols="12" md="6" v-if="showCs">
          <v-text-field
            v-model="subjectCs"
            :label="$t('annotations.labels.subject') + `${inCs} *`"
            :rules="showCs ? [required] : []"
            maxlength="200"
            counter
          >
          </v-text-field>
        </v-col>
        <v-col cols="12" md="6">
          <v-text-field
            v-model="subjectEn"
            :label="$t('annotations.labels.subject') + `${inEn} *`"
            :rules="[required]"
            maxlength="200"
            counter
          >
          </v-text-field>
        </v-col>
      </v-row>
      <v-row>
        <v-col cols="12" md="6" v-if="showCs">
          <v-textarea
            v-model="shortMessageCs"
            :label="$t('annotations.labels.short_message') + inCs"
            rows="2"
            auto-grow
          >
          </v-textarea>
        </v-col>
        <v-col cols="12" md="6">
          <v-textarea
            v-model="shortMessageEn"
            :label="$t('annotations.labels.short_message') + inEn"
            rows="2"
            auto-grow
            color="primary"
          >
          </v-textarea>
        </v-col>
      </v-row>
      <v-row>
        <v-col cols="12" md="6" v-if="showCs">
          <v-textarea
            v-model="messageCs"
            :label="$t('annotations.labels.message') + inCs"
            rows="4"
            auto-grow
            color="primary"
          >
          </v-textarea>
        </v-col>
        <v-col cols="12" :md="showCs ? 6 : null">
          <v-textarea
            v-model="messageEn"
            :label="$t('annotations.labels.message') + inEn"
            rows="4"
            auto-grow
            color="primary"
          >
          </v-textarea>
        </v-col>
      </v-row>
      <v-row>
        <v-spacer></v-spacer>
        <v-col cols="auto">
          <v-btn @click="$emit('cancel')" color="defaultButton">{{
            $t("cancel")
          }}</v-btn>
        </v-col>
        <v-col cols="auto" v-if="showDeleteButton && annotationId">
          <v-btn @click="deleteAnnotation()" color="error">
            <v-icon size="small" class="mr-2">fa fa-trash</v-icon>
            {{ $t("delete") }}
          </v-btn>
        </v-col>
        <v-col cols="auto">
          <v-btn :disabled="saving || !valid" color="primary" type="submit">
            <v-icon size="small" class="mr-2">fas fa-save</v-icon>
            {{ $t("save") }}
          </v-btn>
        </v-col>
      </v-row>
    </v-container>
  </v-form>
</template>

<script>
import { mapActions, mapGetters, mapState } from "vuex";
import axios from "axios";

export default {
  name: "AnnotationCreateModifyWidget",
  props: {
    platform: { required: false, type: Object },
    annotation: { required: false, type: Object },
    fixPlatform: { type: Boolean, default: false },
    showDeleteButton: { type: Boolean, default: true },
  },
  data() {
    return {
      startDate: null,
      endDate: null,
      annotationId: null,
      subjectCs: "",
      subjectEn: "",
      shortMessageCs: "",
      shortMessageEn: "",
      messageCs: "",
      messageEn: "",
      level: "info",
      endDateMenu: null,
      startDateMenu: null,
      saving: false,
      platformId: null,
      organizationId: null,
      platforms: [],
      loadingPlatforms: false,
      valid: false,
    };
  },
  computed: {
    ...mapState({
      appSelectedOrganizationId: "selectedOrganizationId",
    }),
    ...mapGetters({
      organizationSelected: "organizationSelected",
      selectedOrganization: "selectedOrganization",
      organizations: "organizationItems",
      languages: "activeLanguageCodes",
    }),
    importanceLevels() {
      return [
        {
          value: "info",
          text: this.$t("annotations.labels.level_info"),
          icon: "fa fa-info-circle",
          color: "info",
        },
        {
          value: "important",
          text: this.$t("annotations.labels.level_important"),
          icon: "fa fa-exclamation-triangle",
          color: "warning",
        },
      ];
    },
    annotationData() {
      let data = {
        start_date: this.formattedStartDateComputed || null,
        end_date: this.formattedEndDateComputed || null,
        subject_cs: this.subjectCs,
        subject_en: this.subjectEn,
        short_message_cs: this.shortMessageCs,
        short_message_en: this.shortMessageEn,
        message_en: this.messageEn,
        message_cs: this.messageCs,
        level: this.level,
        platform_id: this.platformId === -1 ? null : this.platformId,
        organization_id:
          this.organizationId === -1 ? null : this.organizationId,
      };
      if (this.annotationId) {
        data["pk"] = this.annotationId;
      }
      return data;
    },
    availablePlatformsUrl() {
      if (this.organizationId !== null) {
        return `/api/organization/${this.organizationId}/all-platform/`;
      }
      return null;
    },
    availablePlatforms() {
      let result = [...this.platforms].sort((a, b) =>
        a.name ? a.name.localeCompare(b.name) : -1,
      );
      result.unshift({ name: this.$t("all"), pk: null, extra: true });
      return result;
    },
    showCs() {
      return this.languages.includes("cs");
    },
    inEn() {
      return this.showCs ? ` (${this.$t("in_english")})` : "";
    },
    inCs() {
      return this.showCs ? ` (${this.$t("in_czech")})` : "";
    },
    formattedStartDateComputed() {
      return this.formatDateToDDMMYYYY(this.startDate);
    },
    formattedEndDateComputed() {
      return this.formatDateToDDMMYYYY(this.endDate);
    },
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    save() {
      if (this.annotationId) {
        this.putData();
      } else {
        this.postData();
      }
    },
    validateDateRange() {
      const startDateObj = this.startDate ? new Date(this.startDate) : null;
      const endDateObj = this.endDate ? new Date(this.endDate) : null;

      return startDateObj && endDateObj && startDateObj > endDateObj
        ? this.$t("errors.error_start_after_end")
        : null;
    },
    formatDateToDDMMYYYY(date) {
      if (!date) return "";
      if (typeof date === "object") {
        const Day = String(date.getDate()).padStart(2, "0");
        const Month = String(date.getMonth() + 1).padStart(2, "0");
        const Year = String(date.getFullYear());
        return `${Year}-${Month}-${Day}`;
      } else {
        return date;
      }
    },
    async postData() {
      this.saving = true;
      try {
        let response = await axios.post(
          "/api/annotations/",
          this.annotationData,
        );
        this.annotationId = response.data.pk;
        this.$emit("saved", { annotation: response.data });
        this.showSnackbar({
          content: this.$t("annotations.messages.annotation_created"),
          color: "success",
        });
      } catch (error) {
        this.showSnackbar({
          content: "Error creating annotation: " + error,
          color: "error",
        });
      } finally {
        this.saving = false;
      }
    },
    async putData() {
      this.saving = true;
      try {
        let response = await axios.put(
          `/api/annotations/${this.annotationId}/`,
          this.annotationData,
        );
        this.annotationId = response.data.pk;
        this.$emit("saved", { annotation: response.data });
        this.showSnackbar({
          content: this.$t("annotations.messages.annotation_updated"),
          color: "success",
        });
      } catch (error) {
        this.showSnackbar({
          content: "Error saving annotation: " + error,
          color: "error",
        });
      } finally {
        this.saving = false;
      }
    },
    async fetchPlatforms() {
      if (this.availablePlatformsUrl == null) {
        return null;
      }
      this.platforms = [];
      this.loadingPlatforms = true;
      try {
        let response = await axios.get(this.availablePlatformsUrl);
        this.platforms = response.data;
      } catch (error) {
        this.showSnackbar({
          content: "Error loading platform list: " + error,
          color: "error",
        });
      } finally {
        this.loadingPlatforms = false;
      }
    },
    annotationObjectToData() {
      if (this.annotation) {
        this.annotationId = this.annotation.pk;
        this.startDate = this.annotation.start_date;
        this.endDate = this.annotation.end_date;
        this.subjectCs = this.annotation.subject_cs;
        this.subjectEn = this.annotation.subject_en;
        this.shortMessageCs = this.annotation.short_message_cs;
        this.shortMessageEn = this.annotation.short_message_en;
        this.messageEn = this.annotation.message_en;
        this.messageCs = this.annotation.message_cs;
        this.level = this.annotation.level;
        if (this.annotation.organization) {
          this.organizationId = this.annotation.organization.pk;
        }
        if (this.annotation.platform) {
          this.platformId = this.annotation.platform.pk;
        }
      }
    },
    async deleteAnnotation() {
      if (this.annotationId) {
        try {
          await axios.delete(`/api/annotations/${this.annotationId}/`);
          this.showSnackbar({
            content: this.$t("annotations.messages.annotation_deleted"),
            color: "success",
          });
          this.$emit("deleted");
        } catch (error) {
          this.showSnackbar({
            content: "Error deleting annotation: " + error,
            color: "error",
          });
        }
      }
    },
    required(v) {
      return !!v || this.$t("value_required");
    },
    clean() {
      this.annotationId = null;
      this.organizationId = null;
      this.platformId = null;
      this.startDate = null;
      this.endDate = null;
      this.subjectCs = "";
      this.subjectEn = "";
      this.shortMessageCs = "";
      this.shortMessageEn = "";
      this.messageEn = "";
      this.messageCs = "";
      this.level = "info";
      this.$refs.form.resetValidation();
    },
  },

  watch: {
    annotation() {
      this.annotationObjectToData();
    },
    availablePlatformsUrl() {
      if (this.availablePlatformsUrl) {
        this.fetchPlatforms();
      }
    },
  },

  created() {
    this.fetchPlatforms();
    this.annotationObjectToData();
  },

  mounted() {
    this.platformId = this.platform ? this.platform.pk : null;
    this.organizationId = this.appSelectedOrganizationId;
    this.annotationId = this.annotation ? this.annotation.pk : null;
  },
};
</script>

<style scoped lang="scss"></style>
