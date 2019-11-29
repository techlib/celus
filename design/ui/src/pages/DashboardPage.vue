<i18n lang="yaml" src="../locales/common.yaml"></i18n>

<i18n lang="yaml">
en:
    titles_with_most_interest: Titles with the most interest of this type

cs:
    titles_with_most_interest: Tituly s největším zájmem tohoto typu
</i18n>

<template>
    <v-container fluid>
        <!--v-row>
            <v-col>
                <h1 v-text="$t('pages.dashboard')"></h1>
            </v-col>
        </v-row-->
        <v-row>
            <v-col>
                <v-card>
                    <v-card-title v-text="$t('interest')"></v-card-title>
                    <v-card-text>
                        <APIChart
                                v-if="interestReportType"
                                :organization="organizationId"
                                primary-dimension="date"
                                :report-type-id="interestReportType.pk"
                                secondary-dimension="Interest_Type"
                                raw-report-type
                                stack
                        >
                        </APIChart>
                    </v-card-text>
                </v-card>
            </v-col>
        </v-row>
        <v-row>
            <v-col
                    cols="auto"
                    md_="6"
                    lg_="4"
                    v-for="record in this.interestGroupTitlesSorted"
                    :key="record.interestGroup.short_name"
            >
                <v-card min-height="320px" class="text-center">
                    <v-card-title v-text="record.interestGroup.name"></v-card-title>
                    <v-card-subtitle class="text-left">{{ $t('titles_with_most_interest') }}</v-card-subtitle>
                    <v-card-text>
                        <v-simple-table
                                v-if="record.titles"
                                class="dashoard"
                                dense
                        >
                            <tbody>
                            <tr
                                    v-for="title in record.titles"
                                    :key="title.pk"
                            >
                                <td class="text-left">{{ title.name }}</td>
                                <td class="text-right">{{ formatInteger(title.interests[record.interestGroup.short_name]) }}</td>
                            </tr>
                            </tbody>
                        </v-simple-table>
                        <LargeSpinner v-else />
                    </v-card-text>
                </v-card>
            </v-col>
        </v-row>
    </v-container>
</template>

<script>

  import APIChart from '../components/APIChart'
  import {mapActions, mapGetters, mapState} from 'vuex'
  import axios from 'axios'
  import LargeSpinner from '../components/LargeSpinner'
  import { formatInteger} from '../libs/numbers'

  export default {
    name: "DashboardPage",

    components: {
      LargeSpinner,
      APIChart,
    },

    data () {
      return {
        interestReportType: null,
        interestGroupToTopTitles: {},
      }
    },

    computed: {
      ...mapState({
        organizationId: 'selectedOrganizationId',
        interestGroups: state => state.interest.interestGroups,
      }),
      ...mapGetters({
        dateRangeStart: 'dateRangeStartText',
        dateRangeEnd: 'dateRangeEndText',
      }),
      interestGroupTitlesSorted () {
        let igs = this.interestGroups.filter(item => item.important)
        if (igs) {
          let result = []
          for (let ig of igs.sort((a, b) => a.name > b.name)) {
            if (ig.short_name in this.interestGroupToTopTitles) {
              result.push(this.interestGroupToTopTitles[ig.short_name])
            } else {
              result.push({interestGroup: ig, titles: null})
            }
          }
          return result
        }
        return igs
      },
      titleInterestBaseUrl () {
        return `/api/organization/${this.organizationId}/title-interest/?start=${this.dateRangeStart}&end=${this.dateRangeEnd}&page_size=10&desc=true&page=1`
      }
    },

    methods: {
      ...mapActions({
        fetchInterestReportType: 'fetchInterestReportType',
        showSnackbar: 'showSnackbar',
      }),
      formatInteger: formatInteger,
      async fetchReportTypes () {
        this.interestReportType = await this.fetchInterestReportType()
      },
      async fetchTitlesTopInterest () {
        this.interestGroupToTopTitles = {}
        for (let ig of this.interestGroups) {
          if (ig.important) {
            this.fetchTitleInterest(ig)
          }
        }
      },
      async fetchTitleInterest (interestGroup) {
        let url = this.titleInterestBaseUrl + `&order_by=${interestGroup.short_name}`
        try {
          let response = await axios.get(url)
          this.$set(this.interestGroupToTopTitles, interestGroup.short_name, {
            interestGroup: interestGroup,
            titles: response.data.results,
          })
        } catch (error) {
          this.showSnackbar({content: 'Error loading most interesting titles: '+error, color: 'error'})
        }
      }
    },

    mounted () {
      this.fetchReportTypes()
      this.fetchTitlesTopInterest()
    },

    watch: {
      interestGroups () {
        this.fetchTitlesTopInterest()
      },
      titleInterestBaseUrl () {
        this.fetchTitlesTopInterest()
      }
    }

  }
</script>

<style scoped lang="scss">

    table.dashboard {

        width: 100%;

        th {
            text-align: left;
        }

        td {
            text-align: right;
        }

    }

</style>
