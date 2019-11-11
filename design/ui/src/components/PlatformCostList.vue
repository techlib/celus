<i18n src="../locales/common.yaml"></i18n>

<i18n>
en:
    year: Select year
    columns:
        id: ID
        name: Name
        provider: Provider
        title_count: Title / database count
        sushi_available: SUSHI active
        notes: " "
    sushi_present: SUSHI is available and active for this platform
    no_sushi: SUSHI is not activated for this platform and selected organization
    sushi_for_version: "SUSHI for COUNTER version {version} is available"
    sushi_for_version_outside: "SUSHI not managed by consortium for COUNTER version {version} is available"
    annotations_available: There are annotations for this platform and the current date range. Go to the
        platform page for details.

cs:
    year: Vyberte rok
    columns:
        id: ID
        name: Název
        provider: Poskytovatel
        title_count: Počet titulů a databází
        sushi_available: Aktivní SUSHI
        notes: " "
    sushi_present: SUSHI je pro tuto platformu aktivní
    no_sushi: SUSHI není pro tuto platformu a vybranou organizaci aktivní
    sushi_for_version: "SUSHI pro verzi {version} COUNTERu je k dispozici"
    sushi_for_version_outside: "SUSHI nespravované konsorciem pro verzi {version} COUNTERu je k dispozici"
    annotations_available: Pro tuto platformu a vybrané časové období byly uloženy poznámky.
        Na stránce platformy zjistíte detaily.

</i18n>
<template>
    <v-container fluid class="pt-0">
        <v-row>
            <v-select
                    v-model="selectedYear"
                    :items="availableYears"
                    item-value="year"
                    item-text="year"
                    :label="$t('year')"
            >
            </v-select>
            <v-spacer></v-spacer>
            <v-col class="pt-0">
                <v-text-field
                        v-model="search"
                        append-icon="fa-search"
                        :label="$t('labels.search')"
                        single-line
                        hide-details
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
                        <span v-if="item.interests.loading" class="fas fa-spinner fa-spin subdued" :key="ig.pk"></span>
                        <span v-else :key="ig.pk">
                                {{ formatInteger(item.interests[ig.short_name]) }}
                            </span>
                    </template>
                </v-data-table>
            </v-col>
        </v-row>
    </v-container>
</template>
<script>
  import {mapActions, mapGetters, mapState} from 'vuex'
  import { formatInteger } from '../libs/numbers'
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
        paymentData: {},
        availableYears: [],
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
        return base
      },
      platformToInterest () {
        let platformIdToInterest = {}
        this.interestData.filter(item => item.date__year == this.selectedYear).forEach(item => platformIdToInterest[item.platform] = item)
        return platformIdToInterest

      },
      platformData () {
        let data = [...this.platforms]
        let platformToInterest = this.platformToInterest
        data.forEach(item => item.payment = this.paymentData.price)
        data.forEach(item => item.yearInterest = platformToInterest[item.pk])
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
      async fetchYears () {
        try {
          const response = await axios.get(`/api/organization/${this.selectedOrganizationId}/year-interest/`)
          this.availableYears = response.data
          if (this.availableYears && this.availableYears.length > 0) {
            this.selectedYear = this.availableYears[this.availableYears.length - 1].year
          }
        } catch (error) {
          this.showSnackbar({content: 'Error loading available years: '+error, color: 'error'})
        }
      },
      async fetchInterest () {
        try {
          const response = await axios.get(`/api/organization/${this.selectedOrganizationId}/platform-interest/by-year`)
          this.interestData = response.data
        } catch (error) {
          this.showSnackbar({content: 'Error loading available years: '+error, color: 'error'})
        }
      },
    },
    mounted() {
      this.fetchYears()
      this.fetchInterest()
    }
  }
</script>
<style lang="scss">

    .subdued {
        color: #888888;
    }

</style>
