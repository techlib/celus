<i18n lang="yaml" src="../locales/common.yaml"></i18n>
<i18n lang="yaml" src="../locales/dialog.yaml"></i18n>

<template>
  <v-container align-baseline fluid>
    <v-row align="baseline">
      <v-col v-if="!internalLabel" cols="auto" class="sc px-0" shrink
        >{{ $t("organization") }}:</v-col
      >
      <v-col
        cols="auto"
        :class="{ 'py-0': !internalLabel, 'mt-3': internalLabel }"
      >
        <v-autocomplete
          v-model="orgId"
          :items="items"
          item-text="name"
          item-value="pk"
          clearable
          clear-icon="fa fa-times"
          eager
          :menu-props="{ width: '800px' }"
          :filter="filter"
          :label="label"
          data-tour="organization-select"
          :rules="[required]"
        >
          <template v-slot:item="{ item }">
            <span
              :class="{ bold: item.extra, org: true }"
              v-text="item.name"
            ></span>
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
