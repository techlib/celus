<i18n lang="yaml" src="@/locales/dialog.yaml" />
<i18n lang="yaml" src="@/locales/reporting.yaml" />

<template>
  <v-form v-model="valid" @submit.prevent="update()">
    <v-card class="pa-4">
      <v-card-title>{{ titleTextComputed }}</v-card-title>
      <v-card-text>
        <slot name="top" />
        <v-text-field
          v-model="newTitle"
          :label="inputLabelComputed"
          class="mt-6"
          :rules="[rules.required]"
          ref="title"
        />
        <AccessLevelSelector :value="ownershipType" ref="accessLevel" />
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn @click="cancel()">{{ $t("cancel") }}</v-btn>
        <v-btn
          type="submit"
          color="primary"
          :disabled="!valid || loading"
          :loading="loading"
          >{{ submitButtonText }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-form>
</template>
<script>
import AccessLevelSelector from "@/components/reporting/AccessLevelSelector";
import formRulesMixin from "@/mixins/formRulesMixin";

export default {
  name: "ReportNamingWidget",

  mixins: [formRulesMixin],

  components: { AccessLevelSelector },

  props: {
    name: { type: String, required: false, default: "" },
    ownershipType: { type: String, required: false, default: "user" },
    loading: { type: Boolean, required: false },
    submitText: { type: String, required: false },
    title: { type: String, required: false },
    inputLabel: { type: String, required: false },
  },

  data() {
    return {
      newTitle: this.name,
      valid: false,
    };
  },

  computed: {
    submitButtonText() {
      return this.submitText || this.$t("save");
    },
    titleTextComputed() {
      return this.title || this.$t("copy_report");
    },
    inputLabelComputed() {
      return this.inputLabel || this.$t("new_title");
    },
  },

  mounted() {
    this.$nextTick(() => this.$refs.title.focus());
  },

  methods: {
    cancel() {
      this.$emit("cancel");
    },
    update() {
      this.$emit("update", this.newTitle, this.$refs.accessLevel.valueFromData);
    },
  },
};
</script>
