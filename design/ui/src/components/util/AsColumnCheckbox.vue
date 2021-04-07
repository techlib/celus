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
  <v-tooltip bottom max-width="300px" class="d-inline-block">
    <template #activator="{ on }">
      <span v-on="on">
        <v-checkbox v-model="val" :disabled="inputDisabled" class="pr-4 pl-2">
          <template #label>
            <v-icon small>fa fa-expand-arrows-alt</v-icon>
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
    value: { required: true, type: Boolean },
    disabled: { required: false, default: false, type: Boolean },
    selectedValues: { required: false, default: () => [] },
  },

  data() {
    return {
      val: this.value,
    };
  },

  computed: {
    inputDisabled() {
      return this.disabled;
    },
  },

  watch: {
    val() {
      this.$emit("input", this.val);
    },
    value() {
      this.val = this.value;
    },
  },
};
</script>
