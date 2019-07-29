<i18n src="../locales/common.yaml"></i18n>

<template>

    <v-layout column>
        <v-flex>{{ rangeName }}</v-flex>
        <v-flex class="small subdued">{{ startDate }} - {{ endDate }}</v-flex>
    </v-layout>

</template>

<script>
  import { mapGetters, mapState } from 'vuex'
  import { isoDateFormat } from '../libs/dates'

  export default {
    name: 'SelectedDateRangeWidget',
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
      startDate () {
        return isoDateFormat(this.start)
      },
      endDate () {
        return isoDateFormat(this.end)
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
