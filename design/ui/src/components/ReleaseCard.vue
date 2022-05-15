<template>
  <v-card class="mb-6" max-width="900">
    <v-card-title>{{ getTheRightContent(release.title) }}</v-card-title>
    <v-card-subtitle>{{ release.version }}</v-card-subtitle>
    <v-card-text class="pb-0">
      <p v-html="textMarkdownToHtml"></p>
    </v-card-text>
    <v-card-text class="pt-0 pb-0">
      <v-chip-group>
        <v-chip :disabled="!release.is_new_feature">new feature</v-chip>
        <v-chip :disabled="!release.is_update">update</v-chip>
        <v-chip :disabled="!release.is_bug_fix">bug fix</v-chip>
      </v-chip-group>
    </v-card-text>
    <v-card-actions>
      <v-spacer />
      <v-btn
        :to="`/changelog#${versionToAnchor(release.version)}`"
        color="secondary"
        v-text="'changelog'"
      >
      </v-btn>
      <v-btn
        v-for="(link, i) in release.links"
        :key="'link-' + i"
        color="primary"
        :href="link.link"
        target="blank"
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
      let anchor = "version-" + version.replace(/\./g, "_");
      return anchor;
    },
  },
  computed: {
    ...mapState({
      appLanguage: "appLanguage",
    }),
    textMarkdownToHtml() {
      let textHtml = marked.parse(this.getTheRightContent(this.release.text));
      return textHtml;
    },
  },
};
</script>

<style scoped></style>
