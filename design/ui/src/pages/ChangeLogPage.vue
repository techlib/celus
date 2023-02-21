<i18n lang="yaml">
en:
  changelog: Changelog
  changelog_unavailable: Unfortunately, changelog is currently unavailable...
  version: Version
cs:
  changelog: Seznam změn (anglicky)
  changelog_unavailable: Seznam změn je bohužel momentálně nedostupný...
  version: Verze
</i18n>

<template>
  <v-container fluid>
    <v-row>
      <v-col>
        <h2>{{ $t("changelog") }}</h2>
      </v-col>
    </v-row>
    <v-row>
      <v-layout column alig-center>
        <v-flex>
          <v-col>
            <LargeSpinner v-if="changelog === null" />
            <p v-else-if="changelog.length === 0">
              {{ $t("changelog_unavailable") }}
            </p>
            <div v-else>
              <div v-for="(entry, i) in changelog" class="changelog-entry">
                <h2
                  :id="'version-' + swapCharacters(entry.version)"
                  :key="'version-' + i"
                >
                  {{
                    entry.version === "Unreleased"
                      ? entry.version
                      : $t("version") + " " + entry.version
                  }}
                  <DateWithTooltip v-if="entry.date" :date="entry.date" />
                </h2>
                <div
                  v-html="markdownToHtml(entry.markdown)"
                  :key="'markdown-' + i"
                ></div>
              </div>
            </div>
          </v-col>
        </v-flex>
      </v-layout>
    </v-row>
  </v-container>
</template>

<script>
import axios from "axios";
import { marked } from "marked";
import LargeSpinner from "@/components/util/LargeSpinner";
import { mapActions } from "vuex";
import DateWithTooltip from "@/components/util/DateWithTooltip";

export default {
  name: "ChangeLogPage",
  components: {
    DateWithTooltip,
    LargeSpinner,
  },
  data() {
    return {
      changelog: null,
    };
  },
  methods: {
    swapCharacters(string) {
      return string.toLowerCase().replace(" ", "-").replace(/\./g, "_");
    },
    ...mapActions({
      dismissLastRelease: "dismissLastRelease",
      showSnackbar: "showSnackbar",
    }),
    async fetchChangelog() {
      try {
        let response = await axios.get("/api/changelog/");
        this.changelog = response.data;
      } catch (error) {
        this.showSnackbar({
          content: "Error loading releases: " + error,
          color: "error",
        });
      }
    },
    markdownToHtml(content) {
      const renderer = new marked.Renderer();
      renderer.link = (href, title, text) =>
        `<a target="_blank" href="${href}" title="${title}">${text}</a>`;

      let html = marked.parse(content, {
        breaks: false,
        gfm: true,
        renderer: renderer,
      });
      return html;
    },
  },
  mounted() {
    this.fetchChangelog();
    this.dismissLastRelease(true);
  },
  updated() {
    this.$nextTick(() => {
      if (this.$route.hash) {
        const el = document.querySelector(this.$route.hash);
        el && el.scrollIntoView();
      }
    });
  },
};
</script>

<style lang="scss">
.changelog-entry {
  margin-top: 2rem;
  padding-top: 1rem;
  border-top: solid 1px #ccc;
  &:first-child {
    padding-top: 0;
    margin-top: 0;
    border-top: none;
  }

  h2 {
    padding: 1rem 0 0.25rem 0.75rem;
    color: #444;
    font-size: 1.35rem;
  }
  h3 {
    padding: 0.75rem 0 0.25rem 1.5rem;
    color: #444;
  }
  h4 {
    padding: 0.5rem 0 0.125rem 2.5rem;
    color: #444;
  }
  ul {
    color: #555;
    padding-left: 4.5rem;
  }
}
</style>
