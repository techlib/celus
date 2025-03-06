<template>
  <v-sheet width="100%" height="100%" class="pa-3" rounded border>
    <div class="d-flex justify-space-between">
      <v-tooltip location="bottom" v-if="tooltip" max-width="600px">
        <template v-slot:activator="{ props }">
          <div v-bind="props">{{ title }}</div>
        </template>
        <span>{{ tooltip }}</span>
      </v-tooltip>
      <div class="mt-3" v-else>{{ title }}</div>
      <v-switch
        v-if="switchLabel"
        v-model="switchValue"
        :label="switchLabel"
        density="compact"
        class="mt-0 pt-0 ml-3"
        color="primary"
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
    modelValue: { type: Boolean, default: false },
    disabled: { type: Boolean, default: false },
  },

  data() {
    return {
      switchValue: this.modelValue,
    };
  },

  watch: {
    switchValue() {
      this.$emit("update:modelValue", this.switchValue);
    },
    modelValue() {
      this.switchValue = this.modelValue;
    },
  },
};
</script>

<style scoped lang="scss"></style>
