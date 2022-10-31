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
    non_counter_data_h: More information about the expected format of data
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
    text1: Please upload a <strong>CSV</strong>, <strong>TSV</strong> or <strong>XLSX</strong> file with non-COUNTER data for this platform.
    note: Please note that this function is experimental and not all formats are supported.

  counter:
    text1: Reports in <strong>COUNTER</strong> format can be imported from <strong>CSV</strong>, <strong>TSV</strong> or <strong>JSON</strong> files. Files in the Microsoft <strong>Excel format are not supported</strong>.

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
    non_counter_data_h: Více informací o očekávaném formátu dat
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
    text1: Nahrajte prosím soubor ve formátu <strong>CSV</strong>, <strong>TSV</strong> nebo <strong>XLSX</strong> s ne-COUNTER daty pro tuto platformu.
    note: Upozorňujeme, že tato funkce je experimentální a nejsou podporovány všechny možné formáty.

  counter:
    text1: Pro platformy, které jej podporují, můžete data nahrát
      <strong>ve formátu COUNTER</strong> uložená do souboru ve formátu
      <strong>CSV</strong> nebo <strong>TSV</strong>.
</i18n>

<template>
  <div>
    <div v-if="method === 'celus'">
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
    </div>
    <div v-else-if="method === 'counter'">
      <p v-html="$t('counter.text1')"></p>
    </div>
    <div v-else-if="method === 'nibbler'">
      <p v-html="$t('raw.text1')"></p>
      <v-alert type="info" outlined class="mb-0">{{ $t("raw.note") }}</v-alert>
    </div>
  </div>
</template>

<script>
export default {
  name: "CustomUploadInfoWidget",

  props: {
    method: {
      type: String,
      default: "counter",
      validate: (value) => ["counter", "nibbler", "celus"].includes(value),
    },
  },
};
</script>

<style scoped></style>
