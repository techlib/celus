<i18n lang="yaml" src="../../locales/common.yaml"></i18n>
<i18n lang="yaml" src="../../locales/dialog.yaml"></i18n>
<i18n lang="yaml">
en:
  tag_created: Tag was successfully created.
  tag_saved: Tag was successfully saved.

cs:
  tag_created: Štítek byl úspěšně vytvořen.
  tag_saved: Štítek byl úspěšně uložen.
</i18n>

<template>
  <v-form v-model="valid">
    <v-card>
      <v-card-title class="px-7">{{ $t("labels.new_tag") }}</v-card-title>
      <v-card-text>
        <v-container fluid>
          <v-row>
            <v-col>
              <TagClassSelector
                v-model="tagClass"
                :disabled="tag !== null"
                ref="classSelector"
              />
            </v-col>
            <v-col>
              <v-text-field
                v-model="name"
                :label="$t('labels.tag_name')"
                :rules="[rules.required]"
              />
            </v-col>
          </v-row>
          <v-row>
            <v-col>
              <v-text-field v-model="desc" :label="$t('labels.description')" />
            </v-col>
          </v-row>
          <!-- here would be access selectors, but we use the defaults from class instead -->
          <v-row>
            <v-col>
              <ColorEntry v-model="bgColor" :label="$t('labels.tag_color')" />
            </v-col>
            <v-col cols="3" class="align-self-center">
              <TagChip v-if="tagClass" :tag="tagPreview" />
            </v-col>
            <v-col cols="3" class="align-self-center">
              <TagChip v-if="tagClass" :tag="tagPreviewFull" show-class />
            </v-col>
          </v-row>
        </v-container>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn @click="$emit('close')">{{ $t("actions.close") }}</v-btn>
        <v-btn
          color="primary"
          :disabled="!valid"
          @click="saveTag"
          class="ma-3"
          >{{ tag === null ? $t("actions.create") : $t("actions.save") }}</v-btn
        >
      </v-card-actions>
    </v-card>
  </v-form>
</template>
<script>
import cancellation from "@/mixins/cancellation";
import formRulesMixin from "@/mixins/formRulesMixin";
import { mapActions, mapGetters } from "vuex";
import ColorEntry from "@/components/util/ColorEntry";
import TagChip from "@/components/tags/TagChip";
import tagAccessLevels from "@/mixins/tagAccessLevels";
import tagColors from "@/mixins/tagColors";
import { accessLevels } from "@/libs/tags";
import TagClassSelector from "@/components/tags/TagClassSelector";

export default {
  name: "EditTagWidget",
  components: {
    TagClassSelector,
    TagChip,
    ColorEntry,
  },
  mixins: [cancellation, formRulesMixin, tagAccessLevels, tagColors],

  props: {
    tag: { type: Object, required: false, default: null },
  },

  data() {
    return {
      name: "",
      canSee: accessLevels.OWNER,
      canAssign: accessLevels.OWNER,
      tagClass: null,
      valid: false,
      justCreating: false,
      desc: "",
    };
  },

  computed: {
    ...mapGetters({
      selectedOrganization: "selectedOrganization",
    }),
    tagPreview() {
      if (!this.tagClass) {
        return null;
      }
      let data = {
        tag_class: this.tagClass.pk,
        name: this.name,
        text_color: this.textColor,
        bg_color: this.bgColor,
        desc: this.desc,
        can_see: this.canSee,
        can_assign: this.canAssign,
      };
      if (
        [accessLevels.ORG_USERS, accessLevels.ORG_ADMINS].includes(
          this.canAssign
        ) ||
        [accessLevels.ORG_USERS, accessLevels.ORG_ADMINS].includes(this.canSee)
      ) {
        data.owner_org = this.selectedOrganization?.pk;
      }
      return data;
    },
    tagPreviewFull() {
      if (this.tagClass) {
        return {
          ...this.tagPreview,
          tag_class: this.tagClass,
        };
      }
      return null;
    },
  },

  methods: {
    ...mapActions({ showSnackbar: "showSnackbar" }),
    async saveTag() {
      this.justCreating = true;
      let reply;
      if (this.tag) {
        // we have a tag, we will be patching it
        reply = await this.http({
          url: `/api/tags/tag/${this.tag.pk}/`,
          method: "patch",
          data: this.tagPreview,
        });
      } else {
        // creating new tag
        reply = await this.http({
          url: "/api/tags/tag/",
          method: "post",
          data: this.tagPreview,
        });
      }
      if (!reply.error) {
        this.showSnackbar({
          content:
            this.tag === null ? this.$t("tag_created") : this.$t("tag_saved"),
          color: "success",
        });
        this.$emit("saved", reply.response.data);
      }
    },
    clearName() {
      this.name = "";
      this.desc = "";
    },
    changeTag() {
      if (this.tag) {
        this.bgColor = this.tag.bg_color;
        this.name = this.tag.name;
        this.desc = this.tag.desc;
        this.tagClass = this.tag.tag_class;
        this.canAssign = this.tag.can_assign;
        this.canSee = this.tag.can_see;
      }
    },
    async reload() {
      if (this.$refs.classSelector) {
        await this.$refs.classSelector.reload();
      }
    },
  },

  mounted() {
    this.changeTag();
  },

  watch: {
    tag() {
      this.changeTag();
    },
    tagClass() {
      if (!this.tag) {
        // update some stuff to the defaults of the tag class
        if (this.tagClass) {
          this.bgColor = this.tagClass.bg_color;
          this.canSee = this.tagClass.default_tag_can_see;
          this.canAssign = this.tagClass.default_tag_can_assign;
        }
      }
    },
  },
};
</script>
