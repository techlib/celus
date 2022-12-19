<i18n lang="yaml" src="@/locales/common.yaml" />

<template>
  <v-card class="mb-6 pa-4" elevation="5" max-width="900">
    <v-card-title>
      {{ $t("release.version", { number: release.version }) }}
      <v-spacer />
      <span class="ps-6">
        <template v-for="attr in releaseAttrs">
          <v-tooltip bottom v-if="release[`is_${attr.name}`]">
            <template #activator="{ on }">
              <v-chip
                small
                outlined
                class="ps-2 me-1"
                :color="attr.color"
                v-on="on"
              >
                <v-icon class="pe-2 ps-0" small>{{ attr.icon }}</v-icon>
                {{ $t(`release.${attr.name}`) }}
              </v-chip>
            </template>
            <span>{{ $t(`release.${attr.name}_tt`) }}</span>
          </v-tooltip>
        </template>
      </span>
    </v-card-title>
    <v-card-text class="pb-0">
      <p v-html="textMarkdownToHtml" class="markdown"></p>
    </v-card-text>
    <v-card-actions>
      <v-spacer />
      <v-btn
        :to="`/changelog#${versionToAnchor(release.version)}`"
        color="secondary"
        v-text="$t('release.changelog')"
      >
      </v-btn>
      <v-btn
        v-for="(link, i) in release.links"
        :key="'link-' + i"
        color="primary"
        :href="link.link"
        target="_blank"
        v-text="getTheRightContent(link.title)"
      >
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script>
import { marked } from "marked";
import { mapState } from "vuex";

export default {
  name: "ReleaseCard",

  props: ["release"],

  data() {
    return {
      releaseAttrs: [
        { name: "new_feature", color: "success", icon: "fa-plus" },
        { name: "update", color: "info", icon: "fa-arrow-up" },
        { name: "bug_fix", color: "warning", icon: "fa-bug" },
      ],
    };
  },

  methods: {
    getTheRightContent(content) {
      return content[this.appLanguage] ? content[this.appLanguage] : content.en;
    },
    versionToAnchor(version) {
      return "version-" + version.replace(/\./g, "_");
    },
  },

  computed: {
    ...mapState({
      appLanguage: "appLanguage",
    }),
    textMarkdownToHtml() {
      return marked.parse(this.getTheRightContent(this.release.text));
    },
  },
};
</script>

<style scoped></style>
