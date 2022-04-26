<i18n lang="yaml" src="../../locales/common.yaml"></i18n>
<i18n lang="yaml" src="../../locales/dialog.yaml"></i18n>
<i18n lang="yaml">
en:
  tag_class_created: Tag class was successfully created.
  tag_class_saved: Tag class was successfully saved.

cs:
  tag_class_created: Typ štítku byl úspěšně vytvořen.
  tag_class_saved: Typ štítku byl úspěšně uložen.
</i18n>

<template>
  <v-form v-model="valid">
    <v-card>
      <v-card-title class="px-7">{{ $t("labels.new_tag_class") }}</v-card-title>
      <v-card-text>
        <v-container fluid>
          <v-row>
            <v-col>
              <v-select
                v-model="scope"
                :items="scopes"
                :rules="[rules.required]"
                :label="$t('labels.tag_scope')"
                :hint="$t('labels.tag_scope_hint')"
                persistent-hint
                :disabled="!!tagClass"
              />
            </v-col>
            <v-col>
              <v-text-field
                v-model="name"
                :label="$t('labels.tag_class_name')"
                :rules="[rules.required]"
              />
            </v-col>
            <v-col cols="auto">
              <v-checkbox
                v-model="exclusive"
                :label="$t('labels.tag_is_exclusive')"
                :disabled="tagClass && !tagClass.exclusive"
              />
            </v-col>
          </v-row>
          <v-row>
            <v-col>
              <v-text-field v-model="desc" :label="$t('labels.description')" />
            </v-col>
          </v-row>
          <v-row>
            <v-col>
              <TagAccessLevelSelector
                v-model="canModify"
                :label="$t('labels.tag_class_can_modify')"
              />
            </v-col>
            <v-col>
              <TagAccessLevelSelector
                v-model="canCreateTags"
                :label="$t('labels.tag_class_can_create_tags')"
              />
            </v-col>
          </v-row>
          <v-row>
            <v-col>
              <TagAccessLevelSelector
                v-model="defaultTagCanSee"
                :label="$t('labels.tag_can_see')"
              />
            </v-col>
            <v-col>
              <TagAccessLevelSelector
                v-model="defaultTagCanAssign"
                :label="$t('labels.tag_can_assign')"
              />
            </v-col>
          </v-row>
          <v-row>
            <v-col>
              <ColorEntry v-model="bgColor" :label="$t('labels.tag_color')" />
            </v-col>
            <v-col cols="6" class="align-self-center">
              <TagChip :tag="tagClassPreview" />
            </v-col>
          </v-row>
        </v-container>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn @click="$emit('close')">{{ $t("actions.close") }}</v-btn>
        <v-btn color="primary" :disabled="!valid" @click="save" class="ma-3">{{
          tagClass === null ? $t("actions.create") : $t("actions.save")
        }}</v-btn>
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
import TagAccessLevelSelector from "@/components/tags/TagAccessLevelSelector";
import tagColors from "@/mixins/tagColors";
import { accessLevels } from "@/libs/tags";

export default {
  name: "EditTagClassWidget",
  components: { TagAccessLevelSelector, TagChip, ColorEntry },
  mixins: [cancellation, formRulesMixin, tagColors],

  props: {
    tagClass: { type: Object, required: false, default: null },
  },

  data() {
    return {
      name: "",
      canModify: accessLevels.OWNER, // owner
      canCreateTags: accessLevels.OWNER,
      defaultTagCanSee: accessLevels.OWNER,
      defaultTagCanAssign: accessLevels.OWNER,
      valid: false,
      justCreating: false,
      desc: "",
      scope: "title",
      exclusive: true,
    };
  },

  computed: {
    ...mapGetters({
      consortialInstall: "consortialInstall",
      showConsortialStuff: "showConsortialStuff",
    }),
    tagClassPreview() {
      return {
        name: this.name,
        text_color: this.textColor,
        bg_color: this.bgColor,
        desc: this.desc,
        scope: this.scope,
        exclusive: this.exclusive,
        can_modify: this.canModify,
        can_create_tags: this.canCreateTags,
        default_tag_can_see: this.defaultTagCanSee,
        default_tag_can_assign: this.defaultTagCanAssign,
      };
    },
    scopes() {
      return [
        { value: "title", text: this.$t("title") },
        { value: "platform", text: this.$t("platform") },
        ...(this.consortialInstall || this.showConsortialStuff
          ? [{ value: "organization", text: this.$t("organization") }]
          : []),
      ];
    },
  },

  methods: {
    ...mapActions({ showSnackbar: "showSnackbar" }),
    async save() {
      this.justCreating = true;
      let reply;
      if (this.tagClass) {
        // we have an existing instance, we will be patching it
        reply = await this.http({
          url: `/api/tags/tag-class/${this.tagClass.pk}/`,
          method: "patch",
          data: this.tagClassPreview,
        });
      } else {
        // creating new tag
        reply = await this.http({
          url: "/api/tags/tag-class/",
          method: "post",
          data: this.tagClassPreview,
        });
      }
      if (!reply.error) {
        this.showSnackbar({
          content:
            this.tag === null
              ? this.$t("tag_class_created")
              : this.$t("tag_class_saved"),
          color: "success",
        });
        this.$emit("saved", reply.response.data);
      }
    },
    clearName() {
      this.name = "";
      this.desc = "";
    },
    changeTagClass() {
      if (this.tagClass) {
        this.bgColor = this.tagClass.bg_color;
        this.name = this.tagClass.name;
        this.desc = this.tagClass.desc;
        this.exclusive = this.tagClass.exclusive;
        this.scope = this.tagClass.scope;
        this.canCreateTags = this.tagClass.can_create_tags;
        this.canModify = this.tagClass.can_modify;
        this.defaultTagCanSee = this.tagClass.default_tag_can_see;
        this.defaultTagCanAssign = this.tagClass.default_tag_can_assign;
      }
    },
  },

  mounted() {
    this.changeTagClass();
  },

  watch: {
    tagClass() {
      this.changeTagClass();
    },
  },
};
</script>
