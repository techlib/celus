<i18n src="../locales/common.yaml"></i18n>

<i18n>
en:
    select_date_range: Select date range

cs:
    select_date_range: Vyberte rozmezí dat
</i18n>

<template>

    <v-layout column @click="showDialog = true">
        <v-flex>{{ rangeName }}</v-flex>
        <v-flex class="small subdued">{{ rangeValueText }}</v-flex>

    <v-dialog
            v-model="showDialog"
    >
        <v-card>
            <v-card-title>{{ $t('select_date_range') }}</v-card-title>
            <v-divider></v-divider>
            <v-card-text>
                <DateRangeSelector />
            </v-card-text>
            <v-card-actions>
                <v-spacer></v-spacer>
                <v-btn color="primary" text @click="showDialog = false">Close</v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>
    </v-layout>

</template>

<script>
  import { mapGetters, mapState } from 'vuex'
  import { ymDateFormat } from '../libs/dates'
  import DateRangeSelector from './DateRangeSelector'

  export default {
    name: 'SelectedDateRangeWidget',
    components: {DateRangeSelector},
    data () {
      return {
        showDialog: false,
      }
    },
    computed: {
      ...mapState({
        start: 'dateRangeStart',
        end: 'dateRangeEnd',
      }),
      ...mapGetters({
        rangeObject: 'selectedDateRange'
      }),
      rangeName () {
        return this.$i18n.t(this.rangeObject.name)
      },
      rangeValueText () {
        let start = this.startDate
        let end = this.endDate
        if (start || end) {
          return `${start} - ${end}`
        }
        return ''
      },
      startDate () {
        if (this.start) {
          return ymDateFormat(this.start)
        }
        return ''
      },
      endDate () {
        if (this.end) {
          return ymDateFormat(this.end)
        }
        return ''
      }
    }
  }
</script>

<style scoped lang="scss">

    .small {
        font-size: 0.875rem;
    }
    .subdued {
        color: #888888;
    }

</style>
