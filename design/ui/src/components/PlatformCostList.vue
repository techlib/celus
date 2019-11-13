<i18n src="../locales/common.yaml"></i18n>

<i18n>
en:
    year: Select year
    columns:
        id: ID
        name: Name
        price: Price
        price_per_unit: Price per unit
        price_for_interest: Price for
    only_with_price: Show only platforms with price
    weights: Interest weights
    weights_tooltip: When more than one interest is defined for a platform, you can use the
        following weights to influence relative price of units of each interest

cs:
    year: Vyberte rok
    columns:
        id: ID
        name: Název
        price: Cena
        price_per_unit: Cena za jednotku
        price_for_interest: Cena za
    only_with_price: Zobraz jen platformy s cenou
    weights: Váhy typů zájmů
    weights_tooltip: Pokud je pro platformu definováno více druhů zájmu, můžete použít následující
        váhy k nastavení relativní ceny jednotek jednotlivých druhů zájmu.
</i18n>
<template>
    <v-container fluid class="pt-0">
        <v-row>
            <v-col cols="auto">
                <span v-text="$t('year') + ':'" class="mr-2"></span>
                <v-btn-toggle
                        v-model="selectedYear"
                        mandatory
                        dense
                >
                    <v-btn v-for="year in availableYears" :key="year" :value="year" v-text="year"></v-btn>
                </v-btn-toggle>
            </v-col>
            <v-spacer></v-spacer>
            <v-col cols="auto">
                <!--v-text-field
                        v-model="search"
                        append-icon="fa-search"
                        :label="$t('labels.search')"
                        class="pt-0"
                ></v-text-field-->
                <v-switch
                        v-model="onlyWithPrice"
                        :label="$t('only_with_price')"
                        dense
                        class="mt-0"
                >
                </v-switch>
            </v-col>
        </v-row>
        <v-row>
            <v-col cols="auto">
                <v-tooltip bottom>
                    <template v-slot:activator="{on}">
                        <span v-on="on">
                            {{ $t('weights') }}
                            <v-icon small color="blue">fa fa-info-circle</v-icon>:
                        </span>
                    </template>
                    <span v-text="$t('weights_tooltip')"></span>
                </v-tooltip>
            </v-col>
            <v-col cols="6" sm="3" md="2" v-for="group in activeInterestGroups" :key="group.short_name">
                <v-text-field
                        v-model="interestWeights[group.short_name]"
                        :label="group.name"
                        type="number"
                        dense
                >
                </v-text-field>
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
                    <template v-for="ig in activeInterestGroups" v-slot:[slotName(ig)]="{item}">
                        <v-fade-transition :key="ig.pk" leave-absolute>
                            <span v-if="item.interests.loading" class="fas fa-spinner fa-spin subdued" :key="ig.pk+'-'+selectedYear"></span>
                            <span v-else-if="item.yearInterest" :key="ig.pk+'-'+selectedYear">
                                {{ formatInteger(item.yearInterest[ig.short_name]) }}
                            </span>
                            <span v-else :key="ig.pk+'-'+selectedYear">-</span>
                        </v-fade-transition>
                    </template>
                    <template v-for="ig in activeInterestGroups" v-slot:[slotName2(ig)]="{item}">
                        <v-fade-transition :key="ig.pk" leave-absolute>
                            <span v-if="item.price && item.yearInterest && item.yearInterest[ig.short_name]" :key="ig.pk+'-'+selectedYear">
                                {{ item.pricePerUnitInterest[ig.short_name] | smartFormatFloat }}
                            </span>
                            <span v-else :key="ig.pk+'-'+selectedYear">-</span>
                        </v-fade-transition>
                    </template>
                    <template v-for="ig in activeInterestGroups" v-slot:[slotName3(ig)]="{item}">
                        <v-fade-transition :key="ig.pk" leave-absolute>
                            <span v-if="item.price && item.yearInterest && item.yearInterest[ig.short_name]" :key="ig.pk+'-'+selectedYear">
                                {{ formatInteger(item.pricePerUnitInterest[ig.short_name] * item.yearInterest[ig.short_name]) }}
                            </span>
                            <span v-else :key="ig.pk+'-'+selectedYear">-</span>
                        </v-fade-transition>
                    </template>
                    <template v-slot:item.price="{item}">
                        <v-fade-transition leave-absolute>
                            <span :key="selectedYear">{{ formatInteger(item.price) }}</span>
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
    name: 'PlatformCostList',
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
        interestWeights: {},
        onlyWithPrice: false,
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
        for (let ig of this.activeInterestGroups) {
          base.push({
            text: this.$t('columns.price_per_unit') + ": " + ig.name,
            value: 'pricePerUnitInterest.' + ig.short_name,
            class: 'wrap text-xs-right',
            align: 'right',
          })
        }
        for (let ig of this.activeInterestGroups) {
          base.push({
            text: this.$t('columns.price_for_interest') + ": " + ig.name,
            value: 'pricePerInterest.' + ig.short_name,
            class: 'wrap text-xs-right',
            align: 'right',
          })
        }
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
          let totalInterestWeighted = 0
          let totalInterestPlain = 0
          let pricePerUnitInterest = {}
          if (item.yearInterest) {
            for (let ig of this.activeInterestGroups) {
              const weight = (ig.short_name in this.interestWeights) ? this.interestWeights[ig.short_name] : 1;
              totalInterestWeighted += (ig.short_name in item.yearInterest) ? weight * item.yearInterest[ig.short_name] : 0
              totalInterestPlain += (ig.short_name in item.yearInterest) ? item.yearInterest[ig.short_name] : 0
            }
            for (let ig of this.activeInterestGroups) {
              const weight = (ig.short_name in this.interestWeights) ? this.interestWeights[ig.short_name] : 1;
              pricePerUnitInterest[ig.short_name] = item.price * weight / totalInterestWeighted
            }
          }
          item.totalInterest = totalInterestWeighted
          item.pricePerUnit = (item.price && totalInterestPlain) ? item.price / totalInterestPlain : null
          item.pricePerUnitInterest = pricePerUnitInterest
        })
        if (this.onlyWithPrice) {
          data = data.filter(item => item.price && item.price > 0)
        }
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
      slotName2 (ig) {
        return 'item.pricePerUnitInterest.' + ig.short_name
      },
      slotName3 (ig) {
        return 'item.pricePerInterest.' + ig.short_name
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
      syncInterestWeights () {
        this.activeInterestGroups.forEach(item => {
          if (!(item.short_name in this.interestWeights)) {
            this.$set(this.interestWeights, item.short_name, "1")
          }
        })
      }
    },
    filters: {
      smartFormatFloat,
    },
    mounted() {
      this.fetchInterest()
      this.fetchPayments()
      this.syncInterestWeights()
    },
    watch: {
      selectedOrganizationId () {
        this.fetchInterest()
        this.fetchPayments()
      },
      activeInterestGroups () {
        this.syncInterestWeights()
      }
    }
  }
</script>
<style lang="scss">

    .subdued {
        color: #888888;
    }

</style>
