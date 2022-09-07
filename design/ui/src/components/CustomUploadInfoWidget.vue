<i18n lang="yaml">
en:
  tabs:
    non_counter: Non-counter
    counter: Counter
    raw: From file

  description: For correct import of data, it is necessary to provide data in the <strong>right format</strong>.

  non_counter:
    part1:
      For platforms that do not use COUNTER, you need to <strong>prepare data according to the rules below</strong>.
      Files in the Microsoft <strong>Excel format are not supported</strong>.
    non_counter_data_h: non-COUNTER data
    non_counter_data:
      Because of the large variability in formats that providers use to deliver non-COUNTER
      data, it is not possible to implement support for all of them. Instead, you have to convert
      the data into a common format described below.
      <br><br>
      <em>Note</em> - It is often most practical to prepare your data in a table editor
      and then export it into the CSV format with the correct parameters.
    ncd_file_format_h: File format
    ncd_file_format:
      For the data to be correctly imported, it is necessary to use the CSV format with
      the following parameters -
      comma (<code>,</code>) as field separator, double quotes (<code>"</code>) for text
      quotation.
    ncd_file_content_h: File content
    ncd_file_content:
      The first row of the table contains a header which describes the meaning of individual
      columns. Data for individual titles, metrics, etc. are stored in separate rows.
      If the file contains data for more than one month, they are stored as part of one
      row in separate columns.
      <br>
      Names of individual columns are defined by the report type used (more exactly the
      the dimensions it contains).
      List of dimensions for a specific report type will be displayed when it is selected from
      the selection in the fields "Standard dimensions" and "Report specific dimensions".
      Besides the columns for individual dimensions, columns for data for individual months
      are supported. These have to be named in the "Month Year" form, e.g. "Jan 2019"
      (month is specified using its English 3-letter abbreviation) or in
      the "YYYY-MM" format, e.g. "2019-01".
      <br><br>
      <em>Note</em> - the order of columns is not important, but their names must strictly
      match the report type specification.
    ncd_file_example_h: Example
    example_img_desc:
      Example with standard dimensions <i>Metric</i> and <i>Title</i> and specific
      dimensions <i>Publisher</i> and <i>Success</i>.

  raw:
    report_type_detected_warning: This function is experimental and may not work for all data formats.
    text1: You can also try to upload the file and Celus will try to guess the report type. The file can be in <strong>CSV</strong>, <strong>TSV</strong> or <strong>XLSX</strong> format.

  counter:
    text1: For platforms that support <strong>COUNTER</strong>, you
      can use COUNTER data saved in <strong>CSV</strong> or <strong>TSV</strong> file.

cs:
  tabs:
    non_counter: Mimo counter
    counter: Counter
    raw: Ze souboru

  description: Pro správné nahrání dat je nutné data nahrát ve <strong>správném formátu</strong>.

  non_counter:
    part1:
      Pro platformy, které nevyužívají standardní formát COUNTER, je třeba data
      <strong>připravit podle níže uvedených pravidel</strong>.
      Soubory ve formátu Microsoft <strong>Excel nejsou podporovány</strong>.
    non_counter_data_h: Data mimo formát COUNTER
    non_counter_data:
      Vzhledem k velké rozmanitosti formátů, ve který poskytovatelé dodávají data mimo formát
      COUNTER není možné implementovat jejich podporu. Je proto nutné pro import data připravit
      do jednotného formátu, který je popsán níže.
      <br><br>
      <em>Poznámka</em> - Data je ideální připravit v tabulkovém editoru a vyexportovat do
      formátu CSV se správným nastavením parametrů ukládání.
    ncd_file_format_h: Formát souboru
    ncd_file_format:
      Pro import musí být data uložena v textovém formátu CSV s následujícími parametry -
      čárka (<code>,</code>) jako oddělovač polí, dvojité uvozovky (<code>"</code>) pro
      uvození textu.
    ncd_file_content_h: Obsah souboru
    ncd_file_content:
      První řádek tabulky obsahuje její hlavičku, která určuje význam jednotlivých sloupců.
      Data pro jednotlivé tituly, metriky, atp. jsou uložena na samostatných řádcích.
      Pokud soubor obsahuje data za více měsíců, jsou uložena vždy v rámci jednoho řádku
      v samostatných sloupcích.
      <br>
      Názvy jednotlivých sloupců jsou dané typem reportu, resp. rozměry, které obsahuje.
      Seznam rozměrů se zobrazí při výběru konkrétního typu reportu v polích
      "Standardní rozměry" a "Rozměry specifické pro report". Kromě sloupců pro jednotlivé
      rozměry jsou podporovány ještě sloupce s daty pro jednotlivé měsíce. Ty musí mít název
      v podobě "Month Year", např. "Jan 2019" (názvy měsíců jsou třípísmenné anglické zkratky)
      a nebo "YYYY-MM", např. "2019-01".
      <br><br>
      <em>Poznámka</em> - pořadí sloupců není důležité, ale jejich názvy musí přesně odpovídat
      specifikaci pro daný typ reportu.
    ncd_file_example_h: Ukázka
    example_img_desc:
      Ukázka se standardními rozměry <i>Metric</i> a <i>Title</i> a specifickými
      rozměry <i>Publisher</i> a <i>Success</i>.

  raw:
    report_type_detected_warning: Tato funkce je pouze experimentalní a nelze ji použít na všechny formáty dat.
    text1: Můžete zkusit nahrát soubor a Celus se pokusí uhádnout jeho typ reportu. Soubor může být ve formátu <strong>CSV</strong>, <strong>TSV</strong> nebo <strong>XLSX</strong>.

  counter:
    text1: Pro platformy, které jej podporují, můžete data nahrát
      <strong>ve formátu COUNTER</strong> uložená do souboru ve formátu
      <strong>CSV</strong> nebo <strong>TSV</strong>.
</i18n>

<template>
  <div>
    <p v-html="$t('description')"></p>

    <v-tabs v-model="tab" @change="$emit('input', tabName)" centered>
      <v-tab>
        {{ $t("tabs.non_counter") }}
      </v-tab>
      <v-tab>
        {{ $t("tabs.counter") }}
      </v-tab>
      <v-tab v-if="enableNibbler">
        {{ $t("tabs.raw") }}
      </v-tab>
    </v-tabs>

    <v-tabs-items v-model="tab" class="mt-2">
      <v-tab-item>
        <p v-html="$t('non_counter.part1')"></p>
        <v-expansion-panels>
          <v-expansion-panel>
            <v-expansion-panel-header>
              <h4 v-text="$t('non_counter.non_counter_data_h')"></h4>
            </v-expansion-panel-header>
            <v-expansion-panel-content>
              <p v-html="$t('non_counter.non_counter_data')"></p>
              <h4 v-text="$t('non_counter.ncd_file_format_h')"></h4>
              <p v-html="$t('non_counter.ncd_file_format')"></p>
              <h4 v-text="$t('non_counter.ncd_file_content_h')"></h4>
              <p v-html="$t('non_counter.ncd_file_content')"></p>
              <h4 v-text="$t('non_counter.ncd_file_example_h')"></h4>
              <img
                src="../assets/ex-title-metric-publisher-success.png"
                alt="example"
              />
              <div v-html="$t('non_counter.example_img_desc')"></div>
            </v-expansion-panel-content>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-tab-item>
      <v-tab-item>
        <p v-html="$t('counter.text1')"></p>
      </v-tab-item>
      <v-tab-item v-if="enableNibbler">
        <p v-html="$t('raw.text1')"></p>
        <v-alert type="warning" outlined>
          {{ $t("raw.report_type_detected_warning") }}
        </v-alert>
      </v-tab-item>
    </v-tabs-items>
  </div>
</template>

<script>
import { mapGetters } from "vuex";

export default {
  name: "CustomUploadInfoWidget",
  data() {
    return {
      tab: 0,
    };
  },
  computed: {
    ...mapGetters({
      enableNibbler: "enableNibbler",
    }),
    tabName() {
      switch (this.tab) {
        case 0:
          return "non-counter";
        case 1:
          return "counter";
        case 2:
          return "raw";
        default:
          return null;
      }
    },
  },
};
</script>

<style scoped></style>
