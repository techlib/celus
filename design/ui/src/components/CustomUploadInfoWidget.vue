<i18n>
en:
    part1: XX

cs:
    part1: Tato stránka umožňuje nahrání dat k platformám, které neposkytují rozhraní SUSHI a nebo
           starších dat, která již nejsou na platformě v rámci SUSHI k dispozici.
    part2: Pro správné nahrání dat je nutné data <strong>nahrát ve správném</strong> formátu.
           Pro platformy, které jej podporují, můžete data nahrát
           <strong>ve formátu COUNTER</strong> uložená do souboru ve formátu <strong>CSV</strong>.
           Pro platformy, které nevyužívají standardní formát COUNTER, je třeba data
           <strong>připravit podle níže uvedených pravidel</strong>.
           Soubory ve formátu Microsoft <strong>Excel nejsou podporovány</strong>.
    non_counter_data: XX
</i18n>

<template>
    <div>
        <p v-html="$t('part1')"></p>
        <p v-html="$t('part2')"></p>
    </div>
</template>

<script>
  export default {
    name: "CustomUploadInfoWidget",


  }
</script>

<style scoped>

</style>
