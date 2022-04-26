<i18n lang="yaml" src="../../locales/common.yaml"></i18n>

<template>
  <v-select
    v-model="accessLevel"
    :items="assignableTagAccessLevels"
    :label="label"
    :disabled="assignableTagAccessLevels.length <= 0"
  >
    <template #item="{ item }">
      <v-list-item-content>
        <v-list-item-title>{{ item.text }}</v-list-item-title>
        <v-list-item-subtitle
          v-if="
            item.value === accessLevels.ORG_USERS ||
            item.value === accessLevels.ORG_ADMINS
          "
        >
          {{ selectedOrganization.name }}
        </v-list-item-subtitle>
      </v-list-item-content>
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
    value: { type: Number, default: accessLevels.OWNER },
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
        return this.value;
      },
      set(value) {
        this.$emit("input", value);
      },
    },
  },
};
</script>
