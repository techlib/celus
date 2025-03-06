<i18n lang="yaml" src="@/locales/dialog.yaml"></i18n>

<template>
  <v-autocomplete
    v-model="orgId"
    :items="items"
    item-title="name"
    item-value="pk"
    clearable
    clear-icon="fa fa-times"
    eager
    :filter="filter"
    :label="label"
    :rules="[required]"
    :persistent-hint="persistentHint"
    :hint="hint"
  >
  </v-autocomplete>
</template>

<script>
import { mapGetters } from "vuex";

export default {
  name: "OrganizationSelectionWidget",

  props: {
    modelValue: { required: false },
    label: { default: "organization", type: String },
    hint: { default: null, type: String, required: false },
    persistentHint: { default: false, type: Boolean, required: false },
  },

  data() {
    return {
      orgId: this.modelValue,
    };
  },

  computed: {
    ...mapGetters({
      items: "organizationItems",
    }),
  },
  methods: {
    required(v) {
      return !!v || this.$t("value_required");
    },
    filter(item, queryText) {
      const words = queryText.toLowerCase().split(/ /);
      for (let word of words) {
        if (item.name.toLowerCase().indexOf(word) < 0) return false;
      }
      return true;
    },
  },
  watch: {
    orgId() {
      this.$emit("update:modelValue", this.orgId);
    },
    id() {
      this.orgId = this.id;
    },
  },
};
</script>

<style lang="scss"></style>
