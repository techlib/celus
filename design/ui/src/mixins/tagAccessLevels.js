import { accessLevels } from "@/libs/tags";

export default {
  data() {
    return {
      tagAccessLevels: [
        {
          value: accessLevels.EVERYBODY,
          text: this.$t("tag_access_level.everybody"),
        },
        {
          value: accessLevels.ORG_USERS,
          text: this.$t("tag_access_level.org_users"),
        },
        {
          value: accessLevels.ORG_ADMINS,
          text: this.$t("tag_access_level.org_admins"),
        },
        {
          value: accessLevels.CONS_ADMINS,
          text: this.$t("tag_access_level.cons_admins"),
        },
        { value: accessLevels.OWNER, text: this.$t("tag_access_level.owner") },
        {
          value: accessLevels.SYSTEM,
          text: this.$t("tag_access_level.system"),
        },
      ],
    };
  },

  computed: {
    tagAccessLevelToText() {
      let out = {};
      this.tagAccessLevels.forEach((item) => (out[item.value] = item.text));
      return out;
    },
    assignableTagAccessLevels() {
      // tag access levels the current user can assign to tags
      const org = this.$store.getters.selectedOrganization;
      const user = this.$store.state.user;
      let levels = [accessLevels.OWNER]; // everybody can assign 'owner' level
      if (user.is_superuser || user.is_admin_of_master_organization) {
        levels.push(accessLevels.EVERYBODY);
        levels.push(accessLevels.CONS_ADMINS);
      }
      if (org && org.is_admin) {
        // user is admin of selected organization
        levels.push(accessLevels.ORG_USERS);
        levels.push(accessLevels.ORG_ADMINS);
      }
      return this.tagAccessLevels.filter((item) => levels.includes(item.value));
    },
  },
};
