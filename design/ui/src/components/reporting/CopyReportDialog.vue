<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<i18n lang="yaml" src="@/locales/dialog.yaml"></i18n>

<i18n lang="yaml" src="@/locales/reporting.yaml"></i18n>

<template>
  <v-dialog v-model="show" max-width="640px">
    <ReportNamingWidget
      :loading="justCopying"
      :name="newTitle"
      v-model:ownership-type="ownershipType"
      @cancel="show = false"
      @update="copyReport"
      :copyReport="true"
      :reportAccess="this.report.accessLevel"
    >
      <template #top>
        <span v-text="$t('original_title')"></span>:
        <span class="font-weight-light" v-text="report.name"></span>
      </template>
    </ReportNamingWidget>
  </v-dialog>
</template>

<script>
import cloneDeep from "lodash/cloneDeep";
import { mapState } from "vuex";
import formRulesMixin from "@/mixins/formRulesMixin";
import ReportNamingWidget from "@/components/reporting/ReportNamingWidget.vue";

export default {
  name: "CopyReportDialog",

  mixins: [formRulesMixin],

  components: { ReportNamingWidget },

  props: {
    modelValue: { required: true, type: Boolean },
    report: { required: true, type: Object },
  },

  data() {
    return {
      show: this.modelValue,
      newTitle: this.report.name,
      ownershipType: "user",
      justCopying: false,
      valid: false,
    };
  },

  computed: {
    ...mapState(["user"]),
  },
  methods: {
    async copyReport(title, access) {
      this.justCopying = true;
      let newReport = cloneDeep(this.report);
      newReport.pk = null;
      newReport.name = title;
      newReport.owner = access.owner;
      newReport.ownerOrganization = access.owner_organization;
      try {
        await newReport.save();
        this.$emit("copySuccess", newReport);
      } catch (error) {
        this.$emit("error", error);
      } finally {
        this.justCopying = false;
      }
    },
  },

  watch: {
    modelValue() {
      this.show = this.modelValue;
    },
    show() {
      this.$emit("update:modelValue", this.show);
    },
    report() {
      this.newTitle = this.report.name;
    },
  },
};
</script>
