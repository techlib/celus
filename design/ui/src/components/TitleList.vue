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
                :items-per-page.sync="itemsPerPage"
                :search="search"
                :loading="loading"
                :footer-props="{itemsPerPageOptions: [10, 25, 50, 100]}"
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
            <template v-slot:item.interest="{item}">
                {{ formatInteger(item.interest) }}
            </template>
        </v-data-table>
    </v-card>
</template>

<script>
  import axios from 'axios'
  import { mapActions } from 'vuex'
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
        loading: false,
        showDOI: false,
        selectedPubType: null,
      }
    },
    computed: {
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
        base.push({
            text: this.$i18n.t('columns.interest'),
            value: 'interest',
            align: 'end',

          })
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
        if (this.url) {
          this.loading = true
          try {
            let response = await axios.get(this.url)
            this.titles = response.data
          } catch (error) {
            this.showSnackbar({content: 'Error loading platforms: ' + error})
          } finally {
            this.loading = false
          }
        }
      },
    },
    watch: {
      url () {
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
