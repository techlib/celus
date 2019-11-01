<i18n src="../locales/common.yaml"></i18n>
<i18n src="../locales/pub-types.yaml"></i18n>
<i18n>
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
                :search="search"
                :loading="loading"
                :items-per-page.sync="itemsPerPage"
                :footer-props="{itemsPerPageOptions: [10, 25, 50, 100]}"
                :server-items-length="totalTitleCount"
                :sort-by.sync="sortBy"
                :sort-desc.sync="sortDesc"
                :page.sync="pageNum"
                :must-sort="true"
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
        itemsPerPage: 25,
        totalTitleCount: 0,
        loading: false,
        showDOI: false,
        selectedPubType: null,
        sortBy: 'name',
        sortDesc: true,
        pageNum: 1,
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
      pubTypes () {
        let all = {text: this.$t('pub_type.all'), value: null, icon: 'fa-expand'}
        let usedTypes = new Set()
        this.titles.map(title => usedTypes.add(title.pub_type))
        return [
          all,
          ...pubTypes
            .filter(item => usedTypes.has(item.code))
            .map(item => {return {text: this.$t(item.title), icon: item.icon, value: item.code}})
        ]
      },
      filteredTitles () {
        if (this.selectedPubType === null) {
          return this.titles
        }
        return this.titles.filter(item => item.pub_type === this.selectedPubType)

      },
      fullUrl () {
        if (this.url) {
          let sortBy = this.sortBy
          if (!sortBy) {
            sortBy = ''
          } else if (sortBy.startsWith('interests.')) {
            sortBy = sortBy.replace('interests.', '')
          }
          return this.url + `&page_size=${this.itemsPerPage}&order_by=${sortBy}&desc=${this.sortDesc}&page=${this.pageNum}`
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
        if (this.fullUrl) {
          this.loading = true
          try {
            let response = await axios.get(this.fullUrl)
            this.titles = response.data.results
            this.totalTitleCount = response.data.count
          } catch (error) {
            this.showSnackbar({content: 'Error loading platforms: ' + error})
          } finally {
            this.loading = false
          }
        }
      },
      slotName: ig =>  'item.interests.' + ig.short_name,
    },
    watch: {
      fullUrl () {
        this.loadData()
      }
    },
    mounted() {
      this.loadData()
    }
  }
</script>

<style scoped>

</style>
