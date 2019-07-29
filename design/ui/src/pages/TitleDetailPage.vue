<i18n src="../locales/charts.yaml"></i18n>
<i18n src="../locales/common.yaml"></i18n>

<template>
    <div>
    <v-layout>
        <v-flex>
        <v-breadcrumbs :items="breadcrumbs" class="pl-0">
          <template v-slot:item="props">
            <router-link
                    v-if="props.item.linkName"
                    :to="{name: props.item.linkName, params: props.item.linkParams}"
                    >
                {{ props.item.text }}
            </router-link>
            <span v-else>
                {{ props.item.text }}
            </span>
          </template>
        </v-breadcrumbs>

        <h2 class="mb-4">{{ titleName }}</h2>

        <table class="overview mb-4 elevation-2">
            <tr>
                <th>{{ $t('platform') }}</th>
                <td>{{ platformName }}</td>
            </tr>
            <tr>
                <th>{{ $t('title') }}</th>
                <td>{{ titleName }}</td>
            </tr>
            <template v-if="title">
                <tr v-for="(prop, index) in ['isbn', 'issn', 'eissn']" :key="index">
                    <th>{{ $t('title_fields.'+prop) }}</th>
                    <td>{{ title[prop] }}</td>
                </tr>
            </template>
        </table>
        </v-flex>
        <v-flex shrink v-if="coverUrl">
            <img :src="coverUrl" />
        </v-flex>
    </v-layout>

        <section v-if="selectedOrganization && platformId && titleId">
        <h3>{{ $t('overview') }}</h3>
        <div class="mt-3 mb-3">
            <v-btn-toggle v-model="chartTypeIndex" mandatory>
              <v-btn v-for="(chartType, index) in chartTypes " flat :value="index" :key="index">
                {{ chartType.name }}
              </v-btn>
            </v-btn-toggle>
        </div>

        <APIChart
                report-type-name="TR"
                :primary-dimension="selectedChartType.primary"
                :secondary-dimension="selectedChartType.secondary ? selectedChartType.secondary : null"
                :organization="selectedOrganization.pk"
                :platform="platformId"
                :title="titleId"
            >
        </APIChart>
        </section>
    </div>

</template>

<script>
  import { mapActions, mapGetters } from 'vuex'
  import APIChart from '../components/APIChart'
  import axios from 'axios'

  export default {
    name: 'TitleDetailPage',
    components: {
      APIChart,
    },
    props: {
      'platformId': {required: true, type: Number},
      'titleId': {required: true, type: Number},
      'platformData': {required: false},
    },
    data () {
      return {
        title: null,
        platformDataLocal: null,
        chartTypeIndex: 0,
        chartTypes: [
          {name: this.$i18n.t('chart.date_metric'), primary: 'date', secondary: 'metric'},
          {name: this.$i18n.t('chart.metric'), primary: 'metric'},
          {name: this.$i18n.t('chart.accesstype'), primary: 'Access_Type'},
          {name: this.$i18n.t('chart.accessmethod'), primary: 'Access_Method'},
          {name: this.$i18n.t('chart.datatype'), primary: 'Data_Type'},
          {name: this.$i18n.t('chart.sectiontype'), primary: 'Section_Type'},
        ],
      }
    },
    computed: {
      ...mapGetters({
        selectedOrganization: 'selectedOrganization',
      }),
      selectedChartType () {
        return this.chartTypes[this.chartTypeIndex]
      },
      platform () {
        if (this.platformData) {
          return this.platformData
        }
        return this.platformDataLocal
      },
      platformName () {
        if (this.platform) {
          return this.platform.name
        }
        return ''
      },
      titleName () {
        if (this.title) {
          return this.title.name
        }
        return ''
      },
      breadcrumbs () {
        return [
          {
            text: this.platformName,
            linkName: 'platform-detail',
            linkParams: {
              platformId: this.platformId
            }
          },
          {
            text: this.titleName,
          },
        ]
      },
      coverUrl () {
        if (this.title.isbn) {
          let isbn = this.title.isbn.replace(/-/g, '')
          return `https://covers.openlibrary.org/b/isbn/${isbn}-M.jpg`
        }
        return null
      }
    },
    methods: {
      ...mapActions({
        showSnackbar: 'showSnackbar',
      }),
      loadTitle () {
        if (this.selectedOrganization && this.platformId && this.titleId) {
          axios.get(`/api/organization/${this.selectedOrganization.pk}/platform/${this.platformId}/title/${this.titleId}`)
            .then(response => {
              this.title = response.data
            })
            .catch(error => {
              this.showSnackbar({content: 'Error loading title: '+error})
            })
        }
      },
      loadPlatform () {
        if (this.selectedOrganization) {
          axios.get(`/api/organization/${this.selectedOrganization.pk}/platform/${this.platformId}/`)
            .then(response => {
              this.platformDataLocal = response.data
            })
            .catch(error => {
              this.showSnackbar({content: 'Error loading platforms: '+error})
            })
        }
      }
    },
    created () {
      if (!this.platformData) {
        this.loadPlatform()
      }
      this.loadTitle()
    },
    watch: {
      selectedOrganization () {
        this.loadPlatform()
        this.loadTitle()
      },
    }
  }
</script>

<style scoped lang="scss">

    .thin {
        font-weight: 300;
    }

    table.overview {

        padding: 1rem;

        th {
            text-align: left;
            padding-right: 1.5rem;
        }
    }


</style>
