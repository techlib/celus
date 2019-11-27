<i18n>
en:
    part1: On this page, you can upload data for platforms which do not offer a SUSHI interface
           or older data which are not longer available through SUSHI.
    part2: For correct import of data, it is necessary to provide data in the
           <strong>right format</strong>. For platforms that support <strong>COUNTER</strong>, you
           can use COUNTER data saved in <strong>CSV</strong> file. For platforms that do not use
           COUNTER, you need to <strong>prepare data according to the rules below</strong>.
           Files in the Microsoft <strong>Excell format are not supported</strong>.
    example_img_desc:
           Ukázka se standardními rozměry <i>Metric</i> a <i>Title</i> a specifickými
           rozměry <i>Publisher</i> a <i>Success</i>

cs:
    part1: Tato stránka umožňuje nahrání dat k platformám, které neposkytují rozhraní SUSHI a nebo
           starších dat, která již nejsou na platformě v rámci SUSHI k dispozici.
    part2: Pro správné nahrání dat je nutné data nahrát ve  <strong>správném formátu</strong>.
           Pro platformy, které jej podporují, můžete data nahrát
           <strong>ve formátu COUNTER</strong> uložená do souboru ve formátu <strong>CSV</strong>.
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
    ncd_file_example_h: Ukázka
    example_img_desc:
           Ukázka se standardními rozměry <i>Metric</i> a <i>Title</i> a specifickými
           rozměry <i>Publisher</i> a <i>Success</i>


</i18n>

<template>
    <div>
        <p v-html="$t('part1')"></p>
        <p v-html="$t('part2')"></p>

        <v-expansion-panels>
            <v-expansion-panel>
                <v-expansion-panel-header>
                    <h4 v-text="$t('non_counter_data_h')"></h4>
                </v-expansion-panel-header>
                <v-expansion-panel-content>
                    <p v-html="$t('non_counter_data')"></p>
                    <h4 v-text="$t('ncd_file_format_h')"></h4>
                    <p v-html="$t('ncd_file_format')"></p>
                    <h4 v-text="$t('ncd_file_content_h')"></h4>
                    <p v-html="$t('ncd_file_content')"></p>
                    <h4 v-text="$t('ncd_file_example_h')"></h4>
                    <img src="../assets/ex-title-metric-publisher-success.png" :alt="$t('example_img_desc')" />

                </v-expansion-panel-content>
            </v-expansion-panel>
        </v-expansion-panels>
    </div>
</template>

<script>
  export default {
    name: "CustomUploadInfoWidget",


  }
</script>

<style scoped>

</style>
