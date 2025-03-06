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
      return-object
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
      v-if="ownershipType.value === 'org'"
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
      return ret;
    },
    availableOrganizations() {
      return this.organizationItems
        .filter(
          (item) =>
            item.is_admin ||
            ((this.user.is_superuser ||
              this.user.is_user_of_master_organization) &&
              item.pk !== -1),
        )
        .map((item) => ({ value: item.pk, title: item.name }));
    },
    valueFromData() {
      let ret = { owner: null, owner_organization: null };
      if (this.ownershipType.value === "user") {
        ret["owner"] = this.user.pk;
      } else if (this.ownershipType.value === "org") {
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

  methods: {
    defaultOwnerShip() {
      if (this.copyReport && this.reportAccess && !this.createNew) {
        switch (this.reportAccess) {
          case "org":
            this.ownershipType = {
              value: "org",
              title: this.$t("access_level.org"),
              icon: FlexiReport.accessLeveLToIcon["org"],
            };
            break;
          case "user":
            this.ownershipType = {
              value: "user",
              title: this.$t("access_level.user"),
              icon: FlexiReport.accessLeveLToIcon["user"],
            };
            break;
          case "sys":
            this.ownershipType = {
              value: "sys",
              title: this.$t("access_level.sys"),
              icon: FlexiReport.accessLeveLToIcon["sys"],
            };
            break;
        }
      } else if (!this.copyReport && this.modelValue && !this.createNew) {
        switch (this.modelValue) {
          case "org":
            this.ownershipType = {
              value: "org",
              title: this.$t("access_level.org"),
              icon: FlexiReport.accessLeveLToIcon["org"],
            };
            break;
          case "user":
            this.ownershipType = {
              value: "user",
              title: this.$t("access_level.user"),
              icon: FlexiReport.accessLeveLToIcon["user"],
            };
            break;
          case "sys":
            this.ownershipType = {
              value: "sys",
              title: this.$t("access_level.sys"),
              icon: FlexiReport.accessLeveLToIcon["sys"],
            };
            break;
        }
      } else if (this.createNew) {
        if (this.canCreateConsortialReport) {
          this.ownershipType = {
            value: "sys",
            title: this.$t("access_level.sys"),
            icon: FlexiReport.accessLeveLToIcon["sys"],
          };
        } else if (this.canCreateOrganizationReport) {
          this.ownershipType = {
            value: "org",
            title: this.$t("access_level.org"),
            icon: FlexiReport.accessLeveLToIcon["org"],
          };
        } else {
          this.ownershipType = {
            value: "user",
            title: this.$t("access_level.user"),
            icon: FlexiReport.accessLeveLToIcon["user"],
          };
        }
      }
    },
  },

  created() {
    this.defaultOwnerShip();
  },

  mounted() {
    // Reset value if user doesn't have permissions
    if (!this.ownershipTypes.map((e) => e.value).includes(this.modelValue)) {
      this.ownershipType = this.ownershipTypes[0].value;
    }
  },

  watch: {
    disabled() {
      if (!this.disabled) {
        this.defaultOwnerShip();
      }
    },
    ownerOrganization() {
      this.selectedOrganization = this.ownerOrganization;
    },
    ownershipType(newValue) {
      this.ownershipType = newValue;
      if (this.ownershipType === "org") {
        const firstAdminOrg = this.organizationItems.find(
          (item) => item.is_admin,
        );

        if (firstAdminOrg) {
          this.selectedOrganization = firstAdminOrg.pk;
        } else {
          this.selectedOrganization = null;
        }
      }
      this.$emit("update:modelValue", this.valueFromData);
    },
    selectedOrganization() {
      this.$emit("update:modelValue", this.valueFromData);
    },
  },
};
</script>
