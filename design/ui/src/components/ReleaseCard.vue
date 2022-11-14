<i18n lang="yaml" src="@/locales/common.yaml" />

<template>
  <v-card class="mb-6" max-width="900">
    <v-card-title>
      {{ $t("release.version", { number: release.version }) }}
    </v-card-title>
    <v-card-text class="pb-0">
      <p v-html="textMarkdownToHtml" class="markdown"></p>
    </v-card-text>
    <v-card-text class="pt-0 pb-0">
      <v-chip :disabled="!release.is_new_feature" class="me-1">{{
        $t("release.new_feature")
      }}</v-chip>
      <v-chip :disabled="!release.is_update" class="me-1">{{
        $t("release.update")
      }}</v-chip>
      <v-chip :disabled="!release.is_bug_fix" class="me-1">{{
        $t("release.bug_fix")
      }}</v-chip>
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
