<i18n lang="yaml" src="@/locales/common.yaml" />
<i18n lang="yaml" src="@/locales/dialog.yaml" />
<i18n lang="yaml" src="@/locales/reporting.yaml" />

<template>
  <div :class="disabled ? 'pt-6' : ''">
    <v-select
      v-model="ownershipType"
      :items="ownershipTypes"
      :label="$t('title_fields.access_level')"
      :rules="[rules.required]"
      v-if="!disabled"
    >
      <template #item="{ item }">
        <v-list-item-icon>
          <v-icon color="#999999" class="mr-1 fa-fw" small
            >fa {{ item.icon }}
          </v-icon>
        </v-list-item-icon>

        <v-list-item-content>
          <v-list-item-title>
            {{ item.text }}
          </v-list-item-title>
          <v-list-item-subtitle v-if="!short">
            {{ $t("access_level_tt." + item.value) }}
          </v-list-item-subtitle>
        </v-list-item-content>
      </template>
      <template #selection="{ item }">
        <v-icon color="#999999" class="mr-1 fa-fw" small
          >fa {{ item.icon }}
        </v-icon>
        {{ item.text }}
      </template>
    </v-select>

    <v-tooltip bottom v-else>
      <template #activator="{ on }">
        <span v-on="on">
          <v-icon color="#999999" class="mr-1 fa-fw" small
            >fa {{ icon }}</v-icon
          >
          {{ $t("access_level." + ownershipType) }}
        </span>
      </template>
      {{ $t("access_level_tt." + ownershipType) }}
    </v-tooltip>

    <v-select
      v-model="selectedOrganization"
      :items="availableOrganizations"
      :label="$t('organization')"
      v-if="ownershipType === 'org' && !disabled"
      :rules="[rules.required]"
      :disabled="disabled"
    ></v-select>
    <span v-else-if="disabled && organization">/ {{ organization.name }} </span>
  </div>
</template>
<script>
import { mapGetters, mapState } from "vuex";
import { FlexiReport } from "@/libs/flexi-reports";
import formRulesMixin from "@/mixins/formRulesMixin";

export default {
  name: "AccessLevelSelector",

  mixins: [formRulesMixin],

  props: {
    value: { required: true, type: String },
    ownerOrganization: { required: false, type: Number },
    short: { default: false, type: Boolean },
    disabled: { default: false, type: Boolean },
  },

  data() {
    return {
      ownershipType: this.value,
      selectedOrganization: this.ownerOrganization,
    };
  },

  computed: {
    ...mapState(["user", "organizations"]),
    ...mapGetters(["organizationItems"]),
    canCreateOrganizationReport() {
      if (this.user.is_superuser || this.user.is_admin_of_master_organization) {
        return true;
      }
      if (this.organizationItems.find((item) => item.is_admin)) {
        return true;
      }
      return false;
    },
    canCreateConsortialReport() {
      return (
        this.user.is_superuser || this.user.is_admin_of_master_organization
      );
    },
    ownershipTypes() {
      let ret = [
        {
          value: "user",
          text: this.$t("access_level.user"),
          icon: FlexiReport.accessLeveLToIcon["user"],
        },
      ];
      if (this.canCreateOrganizationReport) {
        ret.push({
          value: "org",
          text: this.$t("access_level.org"),
          icon: FlexiReport.accessLeveLToIcon["org"],
        });
      }
      if (this.canCreateConsortialReport) {
        ret.push({
          value: "sys",
          text: this.$t("access_level.sys"),
          icon: FlexiReport.accessLeveLToIcon["sys"],
        });
      }
      return ret;
    },
    availableOrganizations() {
      return this.organizationItems
        .filter(
          (item) =>
            item.is_admin ||
            ((this.user.is_superuser ||
              this.user.is_user_of_master_organization) &&
              item.pk !== -1)
        )
        .map((item) => ({ value: item.pk, text: item.name }));
    },
    valueFromData() {
      let ret = { owner: null, owner_organization: null };
      if (this.ownershipType === "user") {
        ret["owner"] = this.user.pk;
      } else if (this.ownershipType === "org") {
        ret["owner_organization"] = this.selectedOrganization;
      }
      return ret;
    },
    icon() {
      return FlexiReport.accessLeveLToIcon[this.ownershipType];
    },
    organization() {
      if (this.ownerOrganization) {
        return this.organizations[this.ownerOrganization];
      }
      return null;
    },
  },

  mounted() {
    // Reset value if user doesn't have permissions
    if (!this.ownershipTypes.map((e) => e.value).includes(this.value)) {
      this.ownershipType = this.ownershipTypes[0].value;
    }
  },

  watch: {
    value() {
      this.ownershipType = this.value;
    },
    ownerOrganization() {
      this.selectedOrganization = this.ownerOrganization;
    },
    ownershipType() {
      if (this.ownershipType === "org") {
        // find and select the first organization that the user is admin of
        this.selectedOrganization = this.organizationItems.find(
          (item) => item.is_admin
        ).pk;
      }
      this.$emit("change", this.valueFromData);
    },
    selectedOrganization() {
      this.$emit("change", this.valueFromData);
    },
  },
};
</script>
