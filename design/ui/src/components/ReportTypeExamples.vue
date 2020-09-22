<i18n lang="yaml" src="../locales/dialog.yaml"></i18n>
<i18n lang="yaml">
en:
  title: Report type creation examples
  simple_examples_title: Simple examples
  more_complex_title: More complex example
  ex_metric_text:
    This data contains only the <b>Metric</b> column in addition to the monthly
    columns. As the <b>Metric</b> is together with <b>Title</b> a default column, it is not
    necessary to add any dimensions to the report type when creating it.
  ex_title_text:
    Similarly to the previous example, this table also contains only a default
    column - this time <b>Title</b>. Because of this, no extra dimensions should be added to the
    report type.
  ex_complex_text:
    The above example contains two columns supported by default (<b>Title</b>
    and <b>Metric</b>) and two extra columns (<b>Publisher</b> and <b>Success</b>). In order
    to properly save the data into the database, we must define extra dimensions for these two
    columns by using the <b>Add dimension</b> button. <br> If the desired dimension is already
    used
    elsewhere, we just need to select it from the menu. Otherwise we need to create it. When
    creating a dimension, we have to provide the column name as it appears in the table, that is
    either <b>Publisher</b> or <b>Success</b>. We can also assign a different name under which
    this dimension should be represented in the system - both in English and Czech.
    For example we may decide to use the name <b>Availability</b> for <b>Success</b>.
cs:
  title: Ukázky vytváření typu reportu
  simple_examples_title: Jednoduché případy
  more_complex_title: Složitější případ
  ex_metric_text:
    Výše zobrazená data obsahují kromě sloupců pro jednotlivé měsíce pouze
    sloupec <b>Metric</b>. Protože <b>Metric</b> je spolu s <b>Title</b> standardně podporovaným
    sloupcem, není třeba přidávat žádné další rozměry při vytváření definice reportu.
  ex_title_text:
    Podobně jako v předchozím případě obsahuje tato tabulka jen standardní sloupce
    - tentokrát <b>Title</b>. Z tohoto důvodu není třeba přidávat další rozměry k typu reportu.
    report type.
  ex_complex_text:
    Výše uvedený příklad obsahuje dva standardně podporované sloupce (<b>Title</b>
    a <b>Metric</b>) a dva další sloupce (<b>Publisher</b> a <b>Success</b>). Aby bylo možné
    tato data správně uložit do databáze, je třeba definovat dva další rozměry pro tyto sloupce
    pomocí tlačítka <b>Přidat rozměr</b>. <br>
    Pokud už je daný rozměr použit jinde v systému, je možné jej pouze vybrat z nabízeného menu.
    V opačném případě ho musíme vytvořit. Při vytváření potřebujeme pouze uvést název sloupce,
    pod kterým jsou data uvedena v souboru, tedy <b>Publisher</b> nebo <b>Success</b> v našem případě.
    Můžeme také rozměru přiřadit odlišné jméno, pokud chceme aby byl při rozbrazení v systému
    prezentován jinak - a to v češtině i angličtině. V našem případě se můžeme např. rozhodnout,
    že použijeme název <b>Dostupnost</b> pro sloupec <b>Success</b>.
</i18n>

<template>
  <v-card>
    <v-card-title>{{ $t("title") }}</v-card-title>
    <v-card-text>
      <h3>{{ $t("simple_examples_title") }}</h3>
      <img
        src="../assets/ex-metric.png"
        alt="Example with metric"
        class="mt-4"
      />
      <p v-html="$t('ex_metric_text')"></p>
      <img src="../assets/ex-title.png" alt="Example with title" class="mt-4" />
      <p v-html="$t('ex_title_text')"></p>

      <h3>{{ $t("more_complex_title") }}</h3>
      <img
        src="../assets/ex-title-metric-publisher-success.png"
        alt="Example with metric, title, publisher and success fields"
        class="mt-4"
      />
      <p v-html="$t('ex_complex_text')"></p>
    </v-card-text>
    <v-card-actions>
      <v-spacer></v-spacer>
      <v-btn @click="$emit('close')" class="mr-6 mb-4">{{ $t("close") }}</v-btn>
    </v-card-actions>
  </v-card>
</template>

<script>
export default {
  name: "ReportTypeExamples",
};
</script>

<style scoped></style>
