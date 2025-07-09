<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<i18n lang="yaml" src="@/locales/dialog.yaml"></i18n>

<i18n lang="yaml" src="@/locales/reporting.yaml"></i18n>

<template>
  <div>
    <v-select
      v-model="ownershipType"
      :items="ownershipTypes"
      :label="$t('title_fields.access_level')"
      :rules="[rules.required]"
      :disabled="disabled"
    >
      <template #item="{ item, props }">
        <v-list-item v-bind="props">
          <template #prepend>
            <v-icon color="#999999" class="mr-1 fa-fw" size="small"
              >fa {{ item.raw.icon }}
            </v-icon>
          </template>
          <v-list-item-subtitle v-if="!short">
            {{ $t("access_level_tt." + item.raw.value) }}
          </v-list-item-subtitle>
        </v-list-item>
      </template>
      <template #selection="{ item, props }">
        <v-icon v-bind="props" color="#999999" class="mr-1 fa-fw" size="small"
          >fa {{ item.raw.icon }}
        </v-icon>
        {{ item.raw.title }}
      </template>
    </v-select>
    <v-select
      v-model="selectedOrganization"
      :items="availableOrganizations"
      :label="$t('organization')"
      v-if="ownershipType === 'org'"
      :rules="[rules.required]"
      :disabled="disabled"
    ></v-select>
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
    createdOrg: { type: Number, required: false },
    modelValue: { required: true, type: String },
    ownerOrganization: { required: false, type: Number },
    short: { default: false, type: Boolean },
    disabled: { default: false, type: Boolean },
    copyReport: {
      type: Boolean,
      default: false,
    },
    reportAccess: { type: String, required: false },
    createNew: { type: Boolean, default: false },
  },

  data() {
    return {
      ownershipType: this.modelValue,
      selectedOrganization: this.ownerOrganization || this.createdOrg,
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
          title: this.$t("access_level.user"),
          icon: FlexiReport.accessLeveLToIcon["user"],
        },
      ];
      if (this.canCreateOrganizationReport) {
        ret.push({
          value: "org",
          title: this.$t("access_level.org"),
          icon: FlexiReport.accessLeveLToIcon["org"],
        });
      }
      if (this.canCreateConsortialReport) {
        ret.push({
          value: "sys",
          title: this.$t("access_level.sys"),
          icon: FlexiReport.accessLeveLToIcon["sys"],
        });
      }
      if (
        this.disabled &&
        !ret.some((item) => item.value === this.ownershipType)
      ) {
        ret.push({
          value: this.ownershipType,
          title: this.$t(`access_level.${this.ownershipType}`),
          icon: FlexiReport.accessLeveLToIcon[this.ownershipType],
        });
      }
      return ret;
    },
    availableOrganizations() {
      if (!this.disabled) {
        return this.organizationItems
          .filter(
            (item) =>
              item.is_admin ||
              ((this.user.is_superuser ||
                this.user.is_user_of_master_organization) &&
                item.pk !== -1),
          )
          .map((item) => ({ value: item.pk, title: item.name }));
      } else {
        return this.organizationItems.map((item) => ({
          value: item.pk,
          title: item.name,
        }));
      }
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
    isValidOrg() {
      if (this.ownershipType === "org") {
        return !!this.selectedOrganization;
      }
      return true;
    },
  },

  methods: {
    defaultOwnerShip() {
      if (this.copyReport) {
        if (
          this.ownershipTypes.some((item) => item.value === this.reportAccess)
        ) {
          return (this.ownershipType = this.reportAccess);
        }
        this.ownershipType = this.ownershipTypes.at(-1).value;
      }

      if (!this.copyReport) {
        if (
          this.createNew &&
          this.ownershipTypes.some((item) => item.value === this.ownershipType)
        ) {
          return;
        }
        this.ownershipType = this.ownershipTypes.at(-1).value;
      }
    },
  },

  created() {
    this.defaultOwnerShip();
  },

  watch: {
    modelValue() {
      this.ownershipType = this.modelValue;
    },
    ownerOrganization() {
      this.selectedOrganization = this.ownerOrganization;
    },
    ownershipType(newValue) {
      this.ownershipType = newValue;
      if (newValue === "org") {
        if (
          !this.copyReport ||
          !this.availableOrganizations.some(
            (org) => org.value === this.selectedOrganization,
          )
        ) {
          const firstAdminOrg = this.organizationItems.find(
            (item) => item.is_admin,
          );
          if (firstAdminOrg) {
            this.selectedOrganization = firstAdminOrg.pk;
          } else if (
            this.createdOrg &&
            this.availableOrganizations.some(
              (org) => org.value === this.createdOrg,
            )
          ) {
            this.selectedOrganization = this.createdOrg;
          } else {
            this.selectedOrganization = null;
          }
        }
      }
      this.$emit("update:modelValue", this.valueFromData);
      this.$emit("update:isValidOrg", this.isValidOrg);
    },
    selectedOrganization() {
      this.$emit("update:modelValue", this.valueFromData);
      this.$emit("update:isValidOrg", this.isValidOrg);
    },
  },
};
</script>
