<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<template>
  <v-select
    v-model="accessLevel"
    :items="assignableTagAccessLevels"
    item-title="text"
    :label="label"
    :disabled="assignableTagAccessLevels.length <= 0"
  >
    <template #item="{ props, item }">
      <v-list-item v-bind="props">
        <v-list-item-subtitle
          v-if="
            item.raw.value === accessLevels.ORG_USERS ||
            item.raw.value === accessLevels.ORG_ADMINS
          "
        >
          {{ selectedOrganization.name }}
        </v-list-item-subtitle>
      </v-list-item>
    </template>
  </v-select>
</template>

<script>
import tagAccessLevels from "@/mixins/tagAccessLevels";
import { mapGetters } from "vuex";
import { accessLevels } from "@/libs/tags";

export default {
  name: "TagAccessLevelSelector",

  mixins: [tagAccessLevels],

  props: {
    modelValue: { type: Number, default: accessLevels.OWNER },
    label: { type: String, default: "" },
  },

  data() {
    return {
      accessLevels,
    };
  },

  computed: {
    ...mapGetters({
      selectedOrganization: "selectedOrganization",
    }),
    accessLevel: {
      get() {
        return this.modelValue;
      },
      set(modelValue) {
        this.$emit("update:modelValue", modelValue);
      },
    },
  },
};
</script>
