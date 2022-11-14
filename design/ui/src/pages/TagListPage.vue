<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml">
en:
  hint: You can use the {button} button in the bottom right corner to display help for this page.
  tip: "Tip:"

cs:
  hint: Pomoc k této stránce můžete zobrazit pomocí tlačítka {button} vpravo dole.
  tip: "Tip:"
</i18n>

<template>
  <v-container fluid>
    <v-row justify="space-between">
      <v-col class="pb-0" cols="auto">
        <h2>{{ $t("pages.tags") }}</h2>
      </v-col>
      <v-col cols="auto">
        <v-alert text>
          <span class="font-weight-bold pe-2">{{ $t("tip") }}</span>
          <i18n path="hint">
            <template #button>
              <v-btn color="info" x-small fab>
                <v-icon>fa-question</v-icon>
              </v-btn>
            </template>
          </i18n>
        </v-alert>
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <TagListWidget />
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import TagListWidget from "@/components/tags/TagListWidget";
export default {
  name: "TagListPage",

  components: { TagListWidget },

  data() {
    return {};
  },
};
</script>
