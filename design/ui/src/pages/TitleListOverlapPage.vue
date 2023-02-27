<i18n src="@/locales/common.yaml" lang="yaml"></i18n>
<i18n lang="yaml">
en:
  intro: |
    This tool allows you to upload a CSV file containing a list of titles and
    match them against the titles that you already have available in Celus.
    After processing, the uploaded file will be annotated with the Celus titles
    that match the titles in the uploaded file.
  intro2: |
    You can find more information about the expected file format in
    <a href="https://support.celus.net/support/solutions/articles/103000062844" target="_blank">
      this article</a>.

cs:
  intro: |
    Tento nástroj umožňuje nahrát soubor CSV obsahující seznam titulů a
    porovnat je s tituly, které již máte v Celusu. Po zpracování bude nahraný
    soubor anotován informací o titulech z Celusu, které odpovídají titulům v
    nahraném souboru.
  intro2: |
    Více informací o očekávaném formátu souboru naleznete v
    <a href="https://support.celus.net/support/solutions/articles/103000062844" target="_blank">
      tomto článku</a>.
</i18n>

<template>
  <v-container fluid>
    <v-row>
      <v-col>
        <h2>{{ $t("pages.title_list_overlap") }}</h2>
      </v-col>
    </v-row>
    <v-row>
      <v-col>{{ $t("intro") }}</v-col>
    </v-row>
    <v-row>
      <v-col cols="auto" class="pe-0">
        <v-icon color="warning" class="ps-1">fa-lightbulb</v-icon>
      </v-col>
      <v-col>
        <div v-html="$t('intro2')"></div>
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <TitleOverlapBatchList />
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import TitleOverlapBatchList from "@/components/overlap/TitleOverlapBatchList";

export default {
  name: "TitleListOverlapPage",

  components: { TitleOverlapBatchList },
};
</script>

<style scoped></style>
