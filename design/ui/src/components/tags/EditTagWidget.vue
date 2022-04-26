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
              <v-select
                v-model="tagClass"
                :items="tagClasses"
                item-text="name"
                item-value="pk"
                :loading="tagClassesLoading"
                :label="$t('labels.tag_class')"
                :rules="[rules.required]"
                :disabled="tag !== null"
              >
                <template #item="{ item }">
                  <v-list-item-content>
                    <v-list-item-title>
                      {{ item.name }}
                      <span class="float-right text-caption">{{
                        $t(item.scope)
                      }}</span>
                    </v-list-item-title>
                  </v-list-item-content>
                </template>

                <template #append-item>
                  <v-list-item-content>
                    <v-list-item-title>
                      <AddTagClassButton
                        small
                        class="ml-4"
                        @saved="assignNewClass"
                      />
                    </v-list-item-title>
                  </v-list-item-content>
                </template>
              </v-select>
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
              <TagChip :tag="tagPreview" />
            </v-col>
            <v-col cols="3" class="align-self-center">
              <TagChip v-if="tagClassFull" :tag="tagPreviewFull" show-class />
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
import AddTagClassButton from "@/components/tags/AddTagClassButton";
import tagAccessLevels from "@/mixins/tagAccessLevels";
import TagAccessLevelSelector from "@/components/tags/TagAccessLevelSelector";
import tagColors from "@/mixins/tagColors";
import { accessLevels } from "@/libs/tags";

export default {
  name: "EditTagWidget",
  components: {
    TagAccessLevelSelector,
    AddTagClassButton,
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
      tagClasses: [],
      tagClassesLoading: false,
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
      let data = {
        tag_class: this.tagClass,
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
    tagClassFull() {
      return this.tagClasses.find((cls) => cls.pk === this.tagClass);
    },
    tagPreviewFull() {
      if (this.tagClassFull) {
        return {
          ...this.tagPreview,
          tag_class: this.tagClassFull,
        };
      }
    },
  },

  methods: {
    ...mapActions({ showSnackbar: "showSnackbar" }),
    async fetchTagClasses() {
      this.tagClassesLoading = true;
      const reply = await this.http({ url: "/api/tags/tag-class/" });
      this.tagClassesLoading = false;
      if (!reply.error) {
        this.tagClasses = reply.response.data;
      }
    },
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
        this.tagClass = this.tag.tag_class.pk;
        this.canAssign = this.tag.can_assign;
        this.canSee = this.tag.can_see;
      }
    },
    assignNewClass(newClass) {
      this.tagClasses.push(newClass);
      this.tagClasses.sort((a, b) => a.name.localeCompare(b.name));
      this.tagClass = newClass.pk;
    },
    async reload() {
      await this.fetchTagClasses();
    },
  },

  mounted() {
    this.fetchTagClasses();
    this.changeTag();
  },

  watch: {
    tag() {
      this.changeTag();
    },
    tagClass() {
      if (!this.tag) {
        // update some stuff to the defaults of the tag class
        const cls = this.tagClasses.find((item) => item.pk === this.tagClass);
        if (cls) {
          this.bgColor = cls.bg_color;
          this.canSee = cls.default_tag_can_see;
          this.canAssign = cls.default_tag_can_assign;
        }
      }
    },
  },
};
</script>
