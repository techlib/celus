<i18n lang="yaml" src="@/locales/common.yaml" />
<i18n lang="yaml" src="@/locales/dialog.yaml" />
<i18n lang="yaml" src="@/locales/reporting.yaml" />

<template>
  <v-dialog v-model="show" max-width="800px">
    <v-card class="pa-2">
      <v-card-title>{{ $t("copy_report") }}</v-card-title>
      <v-card-text>
        <v-form v-model="valid">
          <span v-text="$t('original_title')"></span>:
          <span class="font-weight-light" v-text="report.name"></span>
          <v-text-field
            v-model="newTitle"
            :label="$t('new_title')"
            class="mt-6"
            :rules="[rules.required]"
          />
          <AccessLevelSelector :value="ownershipType" ref="accessLevel" />
        </v-form>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn type="submit" @click="show = false">{{ $t("cancel") }} </v-btn>
        <v-btn
          type="submit"
          @click="copyReport"
          color="primary"
          :disabled="!valid || justCopying"
          :loading="justCopying"
          >{{ $t("copy") }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
<script>
import cloneDeep from "lodash/cloneDeep";
import AccessLevelSelector from "@/components/reporting/AccessLevelSelector";
import { mapState } from "vuex";
import formRulesMixin from "@/mixins/formRulesMixin";

export default {
  name: "CopyReportDialog",

  mixins: [formRulesMixin],

  components: { AccessLevelSelector },

  props: {
    value: { required: true, type: Boolean },
    report: { required: true, type: Object },
  },

  data() {
    return {
      show: this.value,
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
    async copyReport() {
      this.justCopying = true;
      let newReport = cloneDeep(this.report);
      newReport.pk = null;
      newReport.name = this.newTitle;
      let access = this.$refs.accessLevel.valueFromData;
      newReport.owner = access.owner;
      newReport.ownerOrganization = access.owner_organization;
      try {
        newReport.save();
        this.$emit("copySuccess", newReport);
      } catch (error) {
        this.$emit("error", error);
      } finally {
        this.justCopying = false;
      }
    },
  },

  watch: {
    value() {
      this.show = this.value;
    },
    show() {
      this.$emit("input", this.show);
    },
    report() {
      this.newTitle = this.report.name;
    },
  },
};
</script>
