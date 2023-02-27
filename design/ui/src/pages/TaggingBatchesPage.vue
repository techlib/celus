<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml">
en:
  desc1: |
    To apply one tag to many titles at once, you can upload a file identifying the titles.
    The file should be a table in CSV format which should contain at least one column with a title identifier.
    Recognized identifiers are ISSN, eISSN and ISBN, so at least one column should have one of these names.
  desc2: |
    You can find more information about the expected file format in
    <a href="https://support.celus.net/support/solutions/articles/103000062844" target="_blank">
      this article</a>.
  desc3: |
    After you upload the file, it will be pre-processed and you will be able to review the result.
    You can then apply one selected tag to the matched titles. If necessary, you can revert this action later.

cs:
  desc1: |
    Pro aplikaci jednoho štítku na mnoho titulů najednou můžete nahrát soubor, který identifikuje tituly.
    Soubor by měl obsahovat tabulku ve formátu CSV, který by měl obsahovat alespoň jeden sloupec s identifikátorem titulu.
    Podporované identifikátory jsou ISSN, eISSN a ISBN, takže alespoň jeden sloupec by měl mít jeden z těchto názvů.
  desc2: |
    Více informací o očekávaném formátu souboru naleznete v
    <a href="https://support.celus.net/support/solutions/articles/103000062844" target="_blank">
      tomto článku</a>.
  desc3: |
    Po nahrání souboru bude provedeno předzpracování a budete moci zkontrolovat výsledek.
    Poté můžete na nalezené tituly aplikovat zvolený štítek. Tuto akci můžete případně později vrátit zpět.
</i18n>

<template>
  <v-container fluid>
    <v-row>
      <v-col>
        <h2>{{ $t("pages.title_lists") }}</h2>
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <p v-html="$t('desc1')"></p>
        <p v-html="$t('desc2')"></p>
        <p v-html="$t('desc3')"></p>
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <TaggingBatchList />
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import TaggingBatchList from "@/components/tagging-batches/TaggingBatchList";
export default {
  name: "TaggingBatchesPage",
  components: { TaggingBatchList },
};
</script>

<style scoped></style>
