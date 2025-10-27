<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<i18n lang="yaml">
en:
  desc1: |
    To apply tags to many titles at once, you can upload a title list file.
    The file should be a table in CSV format which should contain at least one column with a title identifier.
    Recognized identifiers are ISSN, eISSN and ISBN, so at least one column should have one of these names.
    You can find more information {link}.
  desc2: |
    The tag used to tag the titles may either be selected manually during the upload or read from the file.
    In the latter case, the file should contain a column named "tag" with the tag name.
    You can find more information about the expected file format in {link}.
  desc3: |
    After you upload the file, it will be pre-processed and you will be able to review the result.
    You can then apply the tags to the matched titles. If necessary, you can revert this action later.
  this_article: this article
  here: here

cs:
  desc1: |
    Pro aplikaci štítků na mnoho titulů najednou můžete nahrát soubor, který identifikuje tituly.
    Soubor by měl obsahovat tabulku ve formátu CSV, která by měla obsahovat alespoň jeden sloupec s identifikátorem titulu.
    Podporované identifikátory jsou ISSN, eISSN a ISBN, takže alespoň jeden sloupec by měl mít jeden z těchto názvů.
    Více informací naleznete {link}.
  desc2: |
    Štítek použitý k označení titulů může být buď vybrán ručně během nahrávání nebo přečten z souboru.
    V případě druhého přístupu musí soubor obsahovat sloupec s názvem "tag" s názvem štítku.
    Více informací o očekávaném formátu souboru naleznete v {link}.
  desc3: |
    Po nahrání souboru bude provedeno předzpracování a budete moci zkontrolovat výsledek.
    Poté můžete na nalezené tituly aplikovat štítky. Tuto akci můžete případně později vrátit zpět.
  this_article: tomto článku
  here: zde
</i18n>

<template>
  <v-container fluid>
    <v-row>
      <v-col>
        <h2>{{ $t("pages.title_lists") }}</h2>
      </v-col>
    </v-row>
    <v-row>
      <v-col style="max-width: 1200px">
        <v-alert>
          <p>
            <i18n-t keypath="desc1">
              <template #link>
                <a
                  href="https://support.celus.net/support/solutions/articles/103000251477"
                  target="_blank"
                >
                  {{ $t("here") }}
                </a>
              </template>
            </i18n-t>
          </p>
          <p>
            <i18n-t keypath="desc2">
              <template #link>
                <a
                  href="https://support.celus.net/support/solutions/articles/103000062844"
                  target="_blank"
                  >{{ $t("this_article") }}</a
                >
              </template>
            </i18n-t>
          </p>
          <p v-html="$t('desc3')"></p>
        </v-alert>
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <TaggingBatchList></TaggingBatchList>
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

<style scoped>
p {
  margin-bottom: 16px;
}
</style>
