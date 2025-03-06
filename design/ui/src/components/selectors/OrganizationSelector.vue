<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<i18n lang="yaml" src="@/locales/dialog.yaml"></i18n>

<template>
  <v-container align-baseline fluid>
    <v-row align="baseline">
      <v-col v-if="!internalLabel" class="sc px-0" shrink
        >{{ $t("organization") }}:</v-col
      >
      <v-col :class="{ 'py-0': !internalLabel, 'mt-0': internalLabel }">
        <v-autocomplete
          v-model="orgId"
          :items="items"
          item-title="name"
          item-value="pk"
          clear-icon="fa fa-times"
          eager
          density="comfortable"
          hide-details
          :menu-props="{ width: '800px' }"
          :filter="filter"
          :label="label"
          :rules="[required]"
          :disabled="disabled"
        >
          <template v-slot:item="{ item, props }">
            <v-list-item
              v-bind="props"
              :class="{ bold: item.extra, org: true }"
            ></v-list-item>
          </template>
        </v-autocomplete>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { mapActions, mapGetters, mapState } from "vuex";

export default {
  name: "OrganizationSelector",
  props: {
    lang: { required: false, default: null },
    internalLabel: { default: false, type: Boolean },
    disabled: { default: false, type: Boolean },
  },
  computed: {
    ...mapState({
      selectedOrganizationId: "selectedOrganizationId",
    }),
    ...mapGetters({
      items: "organizationItems",
    }),
    orgId: {
      get() {
        return this.selectedOrganizationId;
      },
      set(value) {
        this.selectOrganization({ id: value });
      },
    },
    label() {
      if (this.internalLabel) return this.$t("organization");
      return null;
    },
  },
  methods: {
    ...mapActions({
      selectOrganization: "selectOrganization",
    }),
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
  watch: {},
};
</script>

<style lang="scss">
.sc {
  font-variant: small-caps;
}

.v-select.v-text-field.short input {
  max-width: 0;
}

.bold {
  font-weight: bold;
}

span.org {
  min-width: 600px;
}
</style>
