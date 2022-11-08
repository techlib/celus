<i18n lang="yaml" src="../locales/common.yaml"></i18n>

<template>
  <v-container fluid>
    <v-row dense>
      <v-col cols="12">
        <span :class="titleClass">{{ $t("interest_types") }}</span
        >:
      </v-col>
    </v-row>
    <v-row dense>
      <v-col cols="auto" v-for="ig in interestGroups" :key="ig.pk">
        <v-checkbox
          v-model="selectedGroups"
          class="small-checkbox"
          :label="ig.name"
          :value="ig.short_name"
          dense
        ></v-checkbox>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { mapActions, mapState } from "vuex";

export default {
  name: "InterestGroupSelector",
  props: {
    titleClass: { default: "font-weight-bold", type: String },
  },
  data() {
    return {
      loading: false,
    };
  },
  computed: {
    ...mapState({
      interestGroups: (state) => state.interest.interestGroups,
      selectedGroupsStore: (state) => state.interest.selectedGroups,
    }),
    selectedGroups: {
      get: function () {
        return this.selectedGroupsStore;
      },
      set: function (value) {
        this.changeSelectedGroups(value);
      },
    },
  },
  methods: {
    ...mapActions("interest", {
      changeSelectedGroups: "changeSelectedGroups",
    }),
  },
};
</script>

<style lang="scss">
.v-input.small-checkbox {
  margin-top: 0;

  .v-input__slot {
    margin-bottom: 0 !important;
    margin-right: 0.5rem;

    .v-input--selection-controls__input {
      margin-right: 0;
    }
  }

  label {
    font-size: 0.875rem;
  }
}
</style>
