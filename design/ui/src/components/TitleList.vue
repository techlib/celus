<i18n lang="yaml" src="../locales/common.yaml"></i18n>
<i18n lang="yaml" src="../locales/pub-types.yaml"></i18n>
<i18n lang="yaml">
en:
    columns:
        interest: Interest
    show_doi: Show DOI
    pub_type_filter: Publication type filter
cs:
    columns:
        interest: Zájem
    show_doi: Zobrazit DOI
    pub_type_filter: Filtr typu publikace
</i18n>


<template>
    <v-card>
        <v-card-title>
            <v-row>
                <v-col cols="auto">
                    <v-select
                            :label="$t('pub_type_filter')"
                            :items="pubTypes"
                            v-model="selectedPubType"
                    >
                        <template v-slot:item="{item}">
                            <v-icon small v-text="item.icon + ' fa-fw'" class="mr-2"></v-icon>
                            {{ item.text }}
                        </template>
                        <template v-slot:selection="{item}">
                            <v-icon small v-text="item.icon + ' fa-fw'" class="mr-2"></v-icon>
                            {{ item.text }}
                        </template>
                    </v-select>
                </v-col>
                <v-col cols="auto">
                    <v-switch v-model="showDOI" :label="$t('show_doi')"></v-switch>
                </v-col>

                <v-spacer></v-spacer>
                <v-col cols="auto">
                    <v-text-field
                            v-model="searchDebounced"
                            append-icon="fa-search"
                            :label="$t('labels.search')"
                            single-line
                            hide-details
                    ></v-text-field>
                </v-col>
            </v-row>
        </v-card-title>
        <v-data-table
                :items="filteredTitles"
                :headers="headers"
                :loading="loading"
                :footer-props="{itemsPerPageOptions: [10, 25, 50, 100]}"
                :server-items-length="totalTitleCount"
                :must-sort="true"
                :items-per-page="25"
                :sort-desc="true"
                sort-by="name"
                :page="1"
                :options.sync="options"
        >
            <template v-slot:item.name="{item}">
                <router-link v-if="platformId" :to="{name: 'platform-title-detail', params: {platformId: platformId, titleId: item.pk}}">
                    <ShortenText :text="item.name" :length="50"/>
                </router-link>
                <router-link v-else :to="{name: 'title-detail', params: {platformId: null, titleId: item.pk}}">
                    <ShortenText :text="item.name" />
                </router-link>
            </template>
            <template v-slot:item.pub_type="{item}">
                <v-tooltip bottom>
                    <template v-slot:activator="{ on }">
                        <v-icon small v-on="on">{{ iconForPubType(item.pub_type) }}</v-icon>
                    </template>

                    <span>{{ $t(titleForPubType(item.pub_type)) }}</span>
                </v-tooltip>
            </template>
            <template v-for="ig in activeInterestGroups" v-slot:[slotName(ig)]="{item}">
                <span v-if="item.interests.loading" class="fas fa-spinner fa-spin subdued" :key="ig.pk"></span>
                <span v-else :key="ig.pk">
                    {{ formatInteger(item.interests[ig.short_name]) }}
                </span>
            </template>
        </v-data-table>
    </v-card>
</template>

<script>
  import axios from 'axios'
  import {mapActions, mapGetters} from 'vuex'
  import debounce from 'lodash/debounce'
  import {formatInteger} from '../libs/numbers'
  import {iconForPubType, pubTypes, titleForPubType} from '../libs/pub-types'
  import ShortenText from './ShortenText'

  export default {
    name: 'TitleList',
    components: {ShortenText},
    props: {
      url: {required: true},
      platformId: {required: false}
    },
    data () {
      return {
        titles: [],
        search: '',
        totalTitleCount: 0,
        loading: false,
        showDOI: false,
        selectedPubType: null,
        searchString: '',
        pubTypes: [],
        options: {
        }
      }
    },
    computed: {
      ...mapGetters({
        activeInterestGroups: 'selectedGroupObjects',
      }),
      searchDebounced: {
        get () {
          return this.search
        },
        set: debounce(function (value) {
          this.search = value
        }, 500)
      },
      headers () {
        let base = [
          {
            text: this.$i18n.t('title_fields.name'),
            value: 'name'
          },
          {
            text: this.$i18n.t('title_fields.type'),
            value: 'pub_type'
          },
          {
            text: this.$i18n.t('title_fields.isbn'),
            value: 'isbn'
          },
          {
            text: this.$i18n.t('title_fields.issn'),
            value: 'issn'
          },
          {
            text: this.$i18n.t('title_fields.eissn'),
            value: 'eissn'
          },
        ]
        if (this.showDOI) {
          base.push({
            text: this.$i18n.t('title_fields.doi'),
            value: 'doi'
          })
        }
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
      filteredTitles () {
        return this.titles
      },
      fullUrl () {
        let { sortBy, sortDesc, page, itemsPerPage } = this.options
        if (this.url) {
          if (!sortBy) {
            sortBy = ''
          } else {
            if (Array.isArray(sortBy)) {
              sortBy = sortBy[0]
            }
            if (sortBy.startsWith('interests.')) {
              sortBy = sortBy.replace('interests.', '')
            }
          }
          if (Array.isArray(sortDesc)) {
            sortDesc = sortDesc[0]
          }
          return this.url + `&page_size=${itemsPerPage}&order_by=${sortBy}&desc=${sortDesc}&page=${page}&q=${this.search}&pub_type=${this.selectedPubType || ''}`
        }
        return this.url
      }
    },
    methods: {
      ...mapActions({
        showSnackbar: 'showSnackbar',
      }),
      formatInteger: formatInteger,
      iconForPubType: iconForPubType,
      titleForPubType: titleForPubType,
      async loadData () {
        // it seems there is an issue in i18n that makes this.$i18n undefined after the
        // await call later on. To make i18n work, we store it here and then pass it on
        // to the extractPubTypes method
        const i18n = this.$i18n
        if (this.fullUrl) {
          this.loading = true
          try {
            let response = await axios.get(this.fullUrl)
            this.titles = response.data.results
            this.totalTitleCount = response.data.count
          } catch (error) {
            this.showSnackbar({content: 'Error loading title list: ' + error})
          } finally {
            this.loading = false
          }

          if (!this.selectedPubType) {
              // if we do not filter by pubType, we extract the available pub types here
              this.pubTypes = this.extractPubTypes(i18n)
            }
        }
      },
      extractPubTypes (i18n) {
        let all = {text: i18n.t('pub_type.all'), value: null, icon: 'fa-expand'}
        return [
          all,
          ...pubTypes
            .map(item => {return {text: i18n.t(item.title), icon: item.icon, value: item.code}})
        ]
      },
      slotName: ig =>  'item.interests.' + ig.short_name,
    },
    watch: {
      fullUrl () {
        this.loadData()
      }
    },
    mounted() {
      // it seems that watching fullUrl is enough
      //this.loadData()
    }
  }
</script>

<style scoped>

</style>
