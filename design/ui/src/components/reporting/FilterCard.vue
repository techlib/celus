<template>
  <v-sheet width="100%" height="100%" class="pa-3" rounded outlined>
    <div class="d-flex justify-space-between">
      <v-tooltip bottom v-if="tooltip" max-width="600px">
        <template v-slot:activator="{ on }">
          <div v-on="on">{{ title }}</div>
        </template>
        <span>{{ tooltip }}</span>
      </v-tooltip>
      <div v-else>{{ title }}</div>

      <v-switch
        v-if="switchLabel"
        v-model="switchValue"
        :label="switchLabel"
        dense
        class="mt-0 pt-0"
        hide-details
        :disabled="disabled"
      >
        <template #label>
          <span class="caption">{{ switchLabel }}</span>
        </template>
      </v-switch>
    </div>

    <slot name="alt_content" v-if="switchValue"></slot>
    <slot v-else></slot>
  </v-sheet>
</template>

<script>
export default {
  name: "FilterCard",

  props: {
    title: { type: String, default: "" },
    tooltip: { type: String, default: "" },
    switchLabel: { type: String, default: "" },
    value: { type: Boolean, default: false },
    disabled: { type: Boolean, default: false },
  },

  data() {
    return {
      switchValue: this.value,
    };
  },

  watch: {
    switchValue() {
      this.$emit("input", this.switchValue);
    },
    value() {
      this.switchValue = this.value;
    },
  },
};
</script>

<style scoped lang="scss"></style>
