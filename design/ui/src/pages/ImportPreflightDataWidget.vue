<i18n lang="yaml">
en:
    output_logs: Generated logs
    imported_months: Data found for months
    overview: Overview
    upload: Upload
    total_hits: Sum of hits
    imported_metrics: Found metrics
    title_count: Title count
    hits: hits

cs:
    output_logs: Vygenerované záznamy
    imported_months: Data nalezena pro měsíce
    overview: Přehled
    upload: Nahrát
    total_hits: Součet zásahů
    imported_metrics: Nalezené metriky
    title_count: Počet titulů
    hits: zásahů
</i18n>


<template>
    <v-container>
        <v-row>
            <v-col cols="auto">
                <v-card hover>
                    <v-card-text>
                        <h4>{{ $t('output_logs') }}</h4>
                        <div class="text-right">{{ preflightData.log_count }}</div>
                    </v-card-text>
                </v-card>
            </v-col>
            <v-col cols="auto">
                <v-card hover>
                    <v-card-text>
                        <h4>{{ $t('total_hits') }}</h4>
                        <div class="text-right">{{ preflightData.hits_total }}</div>
                    </v-card-text>
                </v-card>
            </v-col>

            <v-col cols="auto">
                <v-card hover>
                    <v-card-text>
                        <h4>{{ $t('title_count') }}</h4>
                        <div class="text-right">{{ titleCount }}</div>
                    </v-card-text>
                </v-card>
            </v-col>
        </v-row>
        <v-row>
            <v-col cols="auto">
                <v-card hover>
                    <v-card-text>
                        <h4>{{ $t('imported_months') }}</h4>
                        <div class="text-right">
                        <table style="width: 100%">
                            <tr v-for="rec in monthsSorted" :key="rec.name">
                                <td class="text-left pr-4">{{ rec.name.substring(0, 7) }}</td>
                                <td>{{ rec.value }}</td>
                            </tr>
                        </table>
                        </div>
                    </v-card-text>
                </v-card>
            </v-col>

            <v-col cols="auto">
                <v-card hover>
                    <v-card-text>
                        <h4>{{ $t('imported_metrics') }}</h4>
                        <div class="text-right">
                            <table>
                                <tr v-for="rec in metricsSorted" :key="rec.name">
                                    <td class="text-left pr-4">{{ rec.name }}</td>
                                    <td>{{ rec.value }}</td>
                                </tr>
                            </table>
                        </div>
                    </v-card-text>
                </v-card>
            </v-col>

        </v-row>
    </v-container>
</template>
<script>

  export default {
    name: 'ImportPreflightDataWidget',

    components: {
    },

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
