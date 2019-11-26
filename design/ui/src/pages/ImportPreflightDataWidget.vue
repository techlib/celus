<i18n>
en:
    output_logs: Generated logs
    imported_months: Data found for months
    overview: Overview
    upload: Upload
    total_hits: Sum of hits
    imported_metrics: Found metrics
    title_count: Title count

cs:
    output_logs: Vygenerované záznamy
    imported_months: Data nalezena pro měsíce
    overview: Přehled
    upload: Nahrát
    total_hits: Součet zásahů
    imported_metrics: Nalezené metriky
    title_count: Počet titulů
</i18n>


<template>
    <table>
        <tr>
            <th class="text-left">{{ $t('output_logs') }}</th>
            <td class="text-right">{{ preflightData.log_count }}</td>
        </tr>
        <tr>
            <th class="text-left">{{ $t('total_hits') }}</th>
            <td class="text-right">{{ preflightData.hits_total }}</td>
        </tr>
        <tr>
            <th class="text-left">{{ $t('title_count') }}</th>
            <td class="text-right">{{ titleCount }}</td>
        </tr>
        <tr>
            <th class="text-left">{{ $t('imported_months') }}</th>
            <td>
                <ul class="no-decoration">
                    <li v-for="rec in monthsSorted" :key="rec.name">
                        {{ rec.name.substring(0, 7) }}
                        / <i>{{ rec.value }}</i>
                    </li>
                </ul>
            </td>
        </tr>
        <tr>
            <th class="text-left">{{ $t('imported_metrics') }}</th>
            <td>
                <ul class="no-decoration">
                    <li v-for="rec in metricsSorted" :key="rec.name">
                        {{ rec.name }}
                        / <i>{{ rec.value }}</i>
                    </li>
                </ul>
            </td>
        </tr>
    </table>
</template>
<script>
  export default {
    name: 'ImportPreflightDataWidget',

    props: {
      preflightData: {required: true, type: Object},
    },

    computed: {
      monthsSorted () {
        return Object.entries(this.preflightData.months).map(([key, value]) => {return {name: key, value: value}}).sort((a,b) => a.name > b.name)
      },

      metricsSorted () {
        return Object.entries(this.preflightData.metrics).map(([key, value]) => {return {name: key, value: value}}).sort((a,b) => a.value < b.value)
      },

      titleCount () {
        return Object.keys(this.preflightData.titles).length
      }
    }

  }
</script>
<style scoped lang="scss">

    ul.no-decoration {
        list-style: none;
    }

</style>
