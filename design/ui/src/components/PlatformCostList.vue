<i18n src="../locales/common.yaml"></i18n>

<i18n>
en:
    year: Select year
    columns:
        id: ID
        name: Name
        price: Price
        price_per_unit: Price per unit
    annotations_available: There are annotations for this platform and the current date range. Go to the
        platform page for details.

cs:
    year: Vyberte rok
    columns:
        id: ID
        name: Název
        price: Cena
        price_per_unit: Cena za jednotku
    annotations_available: Pro tuto platformu a vybrané časové období byly uloženy poznámky.
        Na stránce platformy zjistíte detaily.

</i18n>
<template>
    <v-container fluid class="pt-0">
        <v-row>
            <v-col cols="auto">
                <v-select
                    v-model="selectedYear"
                    :items="availableYears"
                    :label="$t('year')"
                    class="short"
                >
                </v-select>
            </v-col>
            <v-spacer></v-spacer>
            <v-col>
                <v-text-field
                        v-model="search"
                        append-icon="fa-search"
                        :label="$t('labels.search')"

                ></v-text-field>
            </v-col>
        </v-row>
        <v-row>
            <v-col>
                <v-data-table
                        :items="platformData"
                        :headers="headers"
                        :hide-default-footer="true"
                        :items-per-page="-1"
                        :search="search"
                        sort-by="name"
                        :loading="loading"
                >
                    <template v-slot:item.name="props">
                        <router-link :to="{name: 'platform-detail', params: {platformId: props.item.pk}}">{{
                            props.item.name }}
                        </router-link>
                    </template>
                    <template v-slot:item.title_count="{item}">
                        <span v-if="item.title_count === 'loading'"
                              class="fas fa-spinner fa-spin subdued"></span>
                        <span v-else>
                            {{ formatInteger(item.title_count) }}
                        </span>
                    </template>
                    <template v-for="ig in activeInterestGroups" v-slot:[slotName(ig)]="{item}">
                        <v-fade-transition :key="ig.pk" leave-absolute>
                            <span v-if="item.interests.loading" class="fas fa-spinner fa-spin subdued" :key="ig.pk+'-'+selectedYear"></span>
                            <span v-else-if="item.yearInterest" :key="ig.pk+'-'+selectedYear">
                                {{ formatInteger(item.yearInterest[ig.short_name]) }}
                            </span>
                            <span v-else :key="ig.pk+'-'+selectedYear">-</span>
                        </v-fade-transition>
                    </template>
                    <template v-slot:item.price="{item}">
                        <v-fade-transition leave-absolute>
                            <span :key="selectedYear">{{ formatInteger(item.price) }}</span>
                        </v-fade-transition>
                    </template>
                    <template v-slot:item.pricePerUnit="{item}">
                        <v-fade-transition leave-absolute>
                            <span :key="selectedYear">{{ item.pricePerUnit | smartFormatFloat }}</span>
                        </v-fade-transition>
                    </template>
                </v-data-table>
            </v-col>
        </v-row>
    </v-container>
</template>
<script>
  import {mapActions, mapGetters, mapState} from 'vuex'
  import { formatInteger, smartFormatFloat } from '../libs/numbers'
  import axios from 'axios'

  export default {
    name: 'PlatformList',
    props: {
      loading: {},
      platforms: {},
    },
    data () {
      return {
        search: '',
        paymentData: [],
        availableYears: [],  // will be computed from payment data
        selectedYear: null,
        interestData: [],
      }
    },
    computed: {
      ...mapState({
        selectedOrganizationId: 'selectedOrganizationId',
      }),
      ...mapGetters({
        formatNumber: 'formatNumber',
        activeInterestGroups: 'selectedGroupObjects',
      }),
      headers () {
        let base = [
          {
            text: this.$i18n.t('columns.name'),
            value: 'name'
          },
        ]
        for (let ig of this.activeInterestGroups) {
          base.push({
            text: ig.name,
            value: 'interests.' + ig.short_name,
            class: 'wrap text-xs-right',
            align: 'right',
          })
        }
        base.push({
          text: this.$t('columns.price'),
          value: 'price',
          align: 'right',
        })
        base.push({
          text: this.$t('columns.price_per_unit'),
          value: 'pricePerUnit',
          align: 'right',
        })
        return base
      },
      platformToInterest () {
        let platformIdToInterest = {}
        this.interestData.filter(item => item.date__year == this.selectedYear).forEach(item => platformIdToInterest[item.platform] = item)
        return platformIdToInterest

      },
      platformToPayment () {
        let platformToPayment = {}
        this.paymentData.filter(item => item.year == this.selectedYear).forEach(item => platformToPayment[item.platform] = item.price)
        return platformToPayment
      },
      platformData () {
        let data = [...this.platforms]
        let platformToInterest = this.platformToInterest
        let platformToPayment = this.platformToPayment
        data.forEach(item => {
          item.price = platformToPayment[item.pk]
          item.yearInterest = platformToInterest[item.pk]
          let totalInterest = 0
          if (item.yearInterest) {
            for (let ig of this.activeInterestGroups) {
              totalInterest += (ig.short_name in item.yearInterest) ? item.yearInterest[ig.short_name] : 0
            }
          }
          item.totalInterest = totalInterest
          item.pricePerUnit = (item.price && totalInterest) ? item.price / totalInterest : null
        })
        return data
      }
    },
    methods: {
      ...mapActions({
        showSnackbar: 'showSnackbar',
      }),
      formatInteger: formatInteger,
      slotName (ig) {
        return 'item.interests.' + ig.short_name
      },
      async fetchInterest () {
        try {
          const response = await axios.get(`/api/organization/${this.selectedOrganizationId}/platform-interest/by-year`)
          this.interestData = response.data
        } catch (error) {
          this.showSnackbar({content: 'Error loading available years: '+error, color: 'error'})
        }
      },
      async fetchPayments () {
        try {
          const response = await axios.get(`/api/organization/${this.selectedOrganizationId}/payments/by-year/`)
          this.paymentData = response.data
          this.availableYears = [...new Set(this.paymentData.map(item => item.year))].sort()
          if (this.availableYears && this.availableYears.length > 0) {
            this.selectedYear = this.availableYears[this.availableYears.length - 1]
          }

        } catch (error) {
          this.showSnackbar({content: 'Error loading payment data: '+error, color: 'error'})
        }
      },
    },
    filters: {
      smartFormatFloat,
    },
    mounted() {
      this.fetchInterest()
      this.fetchPayments()
    },
    watch: {
      selectedOrganizationId () {
        this.fetchInterest()
        this.fetchPayments()
      }
    }
  }
</script>
<style lang="scss">

    .subdued {
        color: #888888;
    }

</style>
