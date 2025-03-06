<i18n lang="yaml">
en:
  as_column: As column
  as_column_tt: Check to make individual values of this dimension create separate columns in the resulting report.
  split: Expand to columns
  no_primary_split: You cannot use the same dimension to define both table rows and columns.

cs:
  as_column: Jako sloupce
</i18n>

<template>
  <v-tooltip location="bottom" max-width="300px" class="d-inline-block">
    <template #activator="{ props }">
      <span v-bind="props">
        <v-checkbox
          v-model="val"
          :disabled="inputDisabled"
          class="pr-4 pl-2"
          color="primary"
        >
          <template #label>
            <v-icon size="small">fa fa-expand-arrows-alt</v-icon>
          </template>
        </v-checkbox>
      </span>
    </template>
    <strong>{{ $t("split") }}</strong>
    <div v-if="disabled">{{ $t("no_primary_split") }}</div>
    <div v-else>{{ $t("as_column_tt") }}</div>
  </v-tooltip>
</template>

<script>
export default {
  name: "AsColumnCheckbox",

  props: {
    modelValue: { required: true, type: Boolean },
    disabled: { required: false, default: false, type: Boolean },
    selectedValues: { required: false, default: () => [] },
  },

  data() {
    return {
      val: this.modelValue,
    };
  },

  computed: {
    inputDisabled() {
      return this.disabled;
    },
  },

  watch: {
    val() {
      this.$emit("update:modelValue", this.val);
    },
    modelValue() {
      this.val = this.modelValue;
    },
  },
};
</script>
