<i18n lang="yaml" src="../locales/common.yaml"></i18n>
<i18n lang="yaml" src="../locales/dialog.yaml"></i18n>
<i18n lang="yaml">
en:
  labels:
    short_message: Annotation preamble
    message: Annotation text
    subject: Title
  level: Importance
  level_info: Info
  level_important: Important
  annotation_created: Annotation was successfully created
  annotation_updated: Annotation was successfully updated
  annotation_deleted: Annotation was successfully deleted
  all: All
cs:
  labels:
    short_message: Krátký úvod zprávy
    message: Text zprávy
    subject: Titulek
  level: Důležitost
  level_info: Informační
  level_important: Důležité
  annotation_created: Poznámka byla úspěšně vytvořena
  annotation_updated: Poznámka byla úspěšně upravena
  annotation_deleted: Poznámka byla úspěšně smazána
  all: Všechny
</i18n>

<template>
  <v-form ref="form">
    <v-container>
      <v-row>
        <v-col>
          <v-autocomplete
            v-model="organizationId"
            :items="organizations"
            item-text="name"
            item-value="pk"
          >
            <template v-slot:item="{ item }">
              <span :class="{ bold: item.extra }">{{ item.name }}</span>
            </template>
          </v-autocomplete>
        </v-col>
        <v-col>
          <v-autocomplete
            v-model="platformId"
            :items="platforms"
            item-text="name"
            item-value="pk"
            :loading="loadingPlatforms"
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
            :label="$t('level')"
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
        <v-col cols="12" md="6">
          <v-text-field
            v-model="subjectCs"
            :label="$t('labels.subject') + ' (' + $t('in_czech') + ') *'"
            :rules="[required]"
            maxlength="200"
            counter
          >
          </v-text-field>
        </v-col>
        <v-col cols="12" md="6">
          <v-text-field
            v-model="subjectEn"
            :label="$t('labels.subject') + ' (' + $t('in_english') + ') *'"
            :rules="[required]"
            maxlength="200"
            counter
          >
          </v-text-field>
        </v-col>
      </v-row>
      <v-row>
        <v-col cols="12" md="6">
          <v-textarea
            v-model="shortMessageCs"
            :label="$t('labels.short_message') + ' (' + $t('in_czech') + ')'"
            rows="2"
            outlined
            auto-grow
          >
          </v-textarea>
        </v-col>
        <v-col cols="12" md="6">
          <v-textarea
            v-model="shortMessageEn"
            :label="$t('labels.short_message') + ' (' + $t('in_english') + ')'"
            rows="2"
            outlined
            auto-grow
          >
          </v-textarea>
        </v-col>
      </v-row>
      <v-row>
        <v-col cols="12" md="6">
          <v-textarea
            v-model="messageCs"
            :label="$t('labels.message') + ' (' + $t('in_czech') + ')'"
            rows="4"
            outlined
            auto-grow
          >
          </v-textarea>
        </v-col>
        <v-col cols="12" md="6">
          <v-textarea
            v-model="messageEn"
            :label="$t('labels.message') + ' (' + $t('in_english') + ')'"
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
        <v-col cols="auto" v-if="annotationId">
          <v-btn @click="deleteAnnotation()" color="error">
            <v-icon small class="mr-2">fa-trash</v-icon>
            {{ $t("delete") }}
          </v-btn>
        </v-col>
        <v-col cols="auto">
          <v-btn :disabled="saving || !valid" @click="save()" color="primary">
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
    }),
    importanceLevels() {
      return [
        {
          value: "info",
          text: this.$t("level_info"),
          icon: "fa-info-circle",
          color: "info",
        },
        {
          value: "important",
          text: this.$t("level_important"),
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
    valid() {
      if (!this.subjectCs || !this.subjectEn) {
        return false;
      }
      return true;
    },
    availablePlatformsUrl() {
      if (this.organizationId !== null) {
        return `/api/organization/${this.organizationId}/all-platform/`;
      }
      return null;
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
          content: this.$t("annotation_created"),
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
          content: this.$t("annotation_updated"),
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
        this.platforms.unshift({ name: this.$t("all"), pk: null, extra: true });
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
            content: this.$t("annotation_deleted"),
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
