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
  <v-form ref="form"
    v-model="valid"
    @submit.prevent="save">
    <v-container fluid>
      <v-row>
        <v-col>
          <v-autocomplete
            v-model="organizationId"
            :items="organizations"
            item-text="name"
            item-value="pk"
            :label="$t('organization')"
          >
            <template v-slot:item="{ item }">
              <span :class="{ bold: item.extra }">{{ item.name }}</span>
            </template>
          </v-autocomplete>
        </v-col>
        <v-col>
          <v-autocomplete
            v-model="platformId"
            :items="availablePlatforms"
            item-text="name"
            item-value="pk"
            :loading="loadingPlatforms"
            :disabled="fixPlatform && platform !== null"
            :label="$t('platform')"
          >
            <template v-slot:item="{ item }">
              <span :class="{ bold: item.extra }">{{ item.name }}</span>
            </template>
          </v-autocomplete>
        </v-col>
      </v-row>
      <v-row>
        <v-col cols="auto">
          <v-menu
            v-model="startDateMenu"
            :close-on-content-click="false"
            :nudge-right="40"
            transition="scale-transition"
            offset-y
            min-width="290px"
          >
            <template v-slot:activator="{ on }">
              <v-text-field
                v-model="startDate"
                :label="$t('title_fields.start_date')"
                prepend-icon="fa-calendar"
                readonly
                v-on="on"
              ></v-text-field>
            </template>
            <v-date-picker
              v-model="startDate"
              no-title
              :locale="$i18n.locale"
            ></v-date-picker>
          </v-menu>
        </v-col>
        <v-col cols="auto">
          <v-menu
            v-model="endDateMenu"
            :close-on-content-click="false"
            :nudge-right="40"
            transition="scale-transition"
            offset-y
            min-width="290px"
          >
            <template v-slot:activator="{ on }">
              <v-text-field
                v-model="endDate"
                :label="$t('title_fields.end_date')"
                prepend-icon="fa-calendar"
                readonly
                v-on="on"
              ></v-text-field>
            </template>
            <v-date-picker
              v-model="endDate"
              no-title
              :locale="$i18n.locale"
            ></v-date-picker>
          </v-menu>
        </v-col>
        <v-spacer></v-spacer>
        <v-col cols="auto">
          <v-select
            :items="importanceLevels"
            :label="$t('annotations.labels.level')"
            v-model="level"
          >
            <template v-slot:item="{ item }">
              <v-icon small class="mr-2" :color="item.color">{{
                item.icon
              }}</v-icon>
              {{ item.text }}
            </template>
            <template v-slot:selection="{ item }">
              <v-icon small class="mr-2" :color="item.color">{{
                item.icon
              }}</v-icon>
              {{ item.text }}
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
            outlined
            auto-grow
          >
          </v-textarea>
        </v-col>
        <v-col cols="12" md="6">
          <v-textarea
            v-model="shortMessageEn"
            :label="$t('annotations.labels.short_message') + inEn"
            rows="2"
            outlined
            auto-grow
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
            outlined
            auto-grow
          >
          </v-textarea>
        </v-col>
        <v-col cols="12" :md="showCs ? 6 : null">
          <v-textarea
            v-model="messageEn"
            :label="$t('annotations.labels.message') + inEn"
            rows="4"
            outlined
            auto-grow
          >
          </v-textarea>
        </v-col>
      </v-row>
      <v-row>
        <v-spacer></v-spacer>
        <v-col cols="auto">
          <v-btn @click="$emit('cancel')" v-text="$t('cancel')"></v-btn>
        </v-col>
        <v-col cols="auto" v-if="showDeleteButton && annotationId">
          <v-btn @click="deleteAnnotation()" color="error">
            <v-icon small class="mr-2">fa-trash</v-icon>
            {{ $t("delete") }}
          </v-btn>
        </v-col>
        <v-col cols="auto">
          <v-btn :disabled="saving || !valid" color="primary" type="submit">
            <v-icon small class="mr-2">fa-save</v-icon>
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
          icon: "fa-info-circle",
          color: "info",
        },
        {
          value: "important",
          text: this.$t("annotations.labels.level_important"),
          icon: "fa-exclamation-triangle",
          color: "warning",
        },
      ];
    },
    annotationData() {
      let data = {
        start_date: this.startDate,
        end_date: this.endDate,
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
      let result = this.platforms.sort((a, b) =>
        a.name ? a.name.localeCompare(b.name) : -1
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
    async postData() {
      this.saving = true;
      try {
        let response = await axios.post(
          "/api/annotations/",
          this.annotationData
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
          this.annotationData
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
          let response = await axios.delete(
            `/api/annotations/${this.annotationId}/`
          );
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
