<i18n lang="yaml" src="../locales/common.yaml"></i18n>

<i18n lang="yaml">
en:
    select_date_range: Select date range

cs:
    select_date_range: Vyberte rozmezí dat
</i18n>

<template>

    <v-container ml-3>
        <v-row align="center">
        <v-col cols="auto" class="pa-0" shrink>
            <span :class="inputLikeLabel ? 'input-like' : 'sc'">
                {{ $t('labels.date_range') }}
            </span><span v-if="!inputLikeLabel">:</span>
        </v-col>
        <v-col cols="auto" class="py-0">
            <v-layout column @click="showDialog = true">
                <v-flex>{{ rangeName }}</v-flex>
                <v-flex class="small subdued">{{ rangeValueText }}</v-flex>

                <v-dialog
                        v-model="showDialog"
                        max-width="520px"
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
        </v-col>
        </v-row>
    </v-container>

</template>

<script>
  import { mapGetters, mapState } from 'vuex'
  import { ymDateFormat } from '../libs/dates'
  import DateRangeSelector from './DateRangeSelector'

  export default {
    name: 'SelectedDateRangeWidget',
    components: {DateRangeSelector},
    props: {
      inputLikeLabel: {default: false, type: Boolean},
    },
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

    span.input-like {
        color: rgba(0, 0, 0, 0.6);
        font-size: 0.75rem;
    }

</style>
