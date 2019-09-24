<i18n src="../locales/common.yaml"></i18n>
<i18n>
en:
    columns:
        id: ID
        name: Name
        provider: Provider
        title_count: Title / database count
        sushi_available: SUSHI active
    sushi_present: SUSHI is available and active for this platform
    no_sushi: SUSHI is not activated for this platform and selected organization

cs:
    columns:
        id: ID
        name: Název
        provider: Poskytovatel
        title_count: Počet titulů a databází
        sushi_available: Aktivní SUSHI
    sushi_present: SUSHI je pro tuto platformu aktivní
    no_sushi: SUSHI není pro tuto platformu a vybranou organizaci aktivní
</i18n>

<template>
    <v-container>
        <v-row>
            <v-col>
                <h2>{{ $t('pages.platforms') }}</h2>
            </v-col>
            <v-spacer></v-spacer>
            <v-col v-if="showAdminStuff && organizationSelected" cols="auto">
                <v-btn @click="showUploadDataDialog = true">
                    <v-icon class="mr-2" small>fa-upload</v-icon>
                    {{ $t('actions.upload_data') }}
                </v-btn>
            </v-col>
        </v-row>
        <v-row>
            <v-col>
                <v-card>
                    <v-card-text>
                        <v-container>
                        <v-row dense>
                            <v-col cols="12">
                                <strong>{{ $t('interest_types') }}</strong>:
                            </v-col>
                            <v-col cols="auto">
                                <v-checkbox v-model="activeInterestTypes" class="small-checkbox" :label="$t('interests.title')" value="title"></v-checkbox>
                            </v-col>
                            <v-col cols="auto">
                                <v-checkbox v-model="activeInterestTypes" class="small-checkbox" :label="$t('interests.database')" value="database"></v-checkbox>
                            </v-col>
                            <v-col cols="auto">
                                <v-checkbox v-model="activeInterestTypes" class="small-checkbox" :label="$t('interests.other')" value="other"></v-checkbox>
                            </v-col>
                        </v-row>
                        <v-row>
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
                        </v-container>
                    <v-data-table
                            :items="platforms"
                            :headers="headers"
                            :hide-default-footer="true"
                            :items-per-page="-1"
                            :search="search"
                            sort-by="name"
                            :loading="loading"
                    >
                        <template v-slot:item.name="props">
                            <router-link :to="{name: 'platform-detail', params: {platformId: props.item.pk}}">{{ props.item.name }}</router-link>
                        </template>
                        <template v-slot:item.title_count="{item}">
                            <span v-if="item.title_count === 'loading'" class="fas fa-spinner fa-spin subdued"></span>
                            <span v-else>
                                {{ formatInteger(item.title_count) }}
                            </span>
                        </template>
                        <template v-slot:item.interests.title="{item}">
                            <span v-if="item.interests.loading" class="fas fa-spinner fa-spin subdued"></span>
                            <span v-else>
                                {{ formatInteger(item.interests.title) }}
                            </span>
                        </template>
                        <template v-slot:item.interests.database="{item}">
                             <span v-if="item.interests.loading" class="fas fa-spinner fa-spin subdued"></span>
                            <span v-else>
                                {{ formatInteger(item.interests.database) }}
                            </span>
                        </template>
                        <template v-slot:item.interests.other="{item}">
                             <span v-if="item.interests.loading" class="fas fa-spinner fa-spin subdued"></span>
                            <span v-else>
                                {{ formatInteger(item.interests.other) }}
                            </span>
                        </template>
                        <template v-slot:item.sushi_credentials_count="{item}">
                            <v-tooltip bottom>
                                <template v-slot:activator="{ on }">
                                    <v-icon x-small v-on="on">{{ item.sushi_credentials_count ? 'fa-check' : typeof item.sushi_credentials_count === 'undefined' ? '': 'fa-times' }}</v-icon>
                                </template>
                                <template>
                                    <span v-if="typeof item.sushi_credentials_count === 'undefined'"></span>
                                    <span v-else-if="item.sushi_credentials_count > 0">{{ $t('sushi_present') }}</span>
                                    <span v-else>{{ $t('no_sushi') }}</span>
                                </template>
                            </v-tooltip>
                        </template>
                    </v-data-table>
                    </v-card-text>

                </v-card>
            </v-col>
        </v-row>
        <v-dialog v-model="showUploadDataDialog" max-width="640px">
            <PlatformSelectionWidget>
                <template v-slot:actions>
                    <v-btn @click="showUploadDataDialog = false">{{ $t('actions.cancel') }}</v-btn>
                </template>
            </PlatformSelectionWidget>
        </v-dialog>
    </v-container>
</template>

<script>
  import { mapActions, mapGetters, mapState } from 'vuex'
  import axios from 'axios'
  import PlatformSelectionWidget from './PlatformSelectionWidget'
  import {formatInteger} from '../libs/numbers'
  import {
    createEmptyInterestRecord,
    createLoadingInterestRecord,
    remapInterestRecord
  } from '../libs/interest'

  export default {
    name: 'PlatformListPage',
    components: {PlatformSelectionWidget},
    data () {
      return {
        platforms: [],
        search: '',
        loading: false,
        showUploadDataDialog: false,
        activeInterestTypes: ['title', 'database'],
      }
    },
    computed: {
      ...mapState({
        selectedOrganizationId: 'selectedOrganizationId',
      }),
      ...mapGetters({
        formatNumber: 'formatNumber',
        dateRangeStart: 'dateRangeStartText',
        dateRangeEnd: 'dateRangeEndText',
        showAdminStuff: 'showAdminStuff',
        organizationSelected: 'organizationSelected',
      }),
      headers () {
        let base = [
          {
            text: this.$i18n.t('columns.name'),
            value: 'name'
          },
          {
            text: this.$i18n.t('columns.provider'),
            value: 'provider'
          },
          {
            text: this.$i18n.t('columns.title_count'),
            value: 'title_count',
            class: 'wrap',
            align: 'right',
          },
        ]
        if (this.activeInterestTypes.indexOf('title') >= 0) {
          base.push({
            text: this.$i18n.t('interests.title'),
            value: 'interests.title',
            class: 'wrap text-xs-right',
            align: 'right',
          })
        }
        if (this.activeInterestTypes.indexOf('database') >= 0) {
          base.push({
            text: this.$i18n.t('interests.database'),
            value: 'interests.database',
            class: 'wrap text-xs-right',
            align: 'right',
          })
        }
        if (this.activeInterestTypes.indexOf('other') >= 0) {
          base.push({
            text: this.$i18n.t('interests.other'),
            value: 'interests.other',
            class: 'wrap text-xs-right',
            align: 'right',
          })
        }
        base.push({
            text: this.$i18n.t('columns.sushi_available'),
            value: 'sushi_credentials_count',
            sortable: false,
          })
        return base
      },
      platformsURL () {
        return `/api/organization/${this.selectedOrganizationId}/platform/?start=${this.dateRangeStart}&end=${this.dateRangeEnd}`
      },
      platformInterestURL () {
        return `/api/organization/${this.selectedOrganizationId}/platform-interest/?start=${this.dateRangeStart}&end=${this.dateRangeEnd}`
      }
    },
    methods: {
      ...mapActions({
        showSnackbar: 'showSnackbar',
      }),
      formatInteger: formatInteger,
      async loadPlatforms () {
        if (this.selectedOrganizationId) {
          this.loading = true
          try {
            let response = await axios.get(this.platformsURL)
            this.platforms = response.data.map(item => {item.interests = createLoadingInterestRecord(); item.title_count = 'loading'; return item})
            this.loadPlatformDetails()
            this.loadPlatformSushiCounts()
          } catch (error) {
              this.showSnackbar({content: 'Error loading platforms: '+error, color: 'error'})
          } finally {
            this.loading = false
          }
        }
      },
      async loadPlatformDetails () {
        try {
          let response = await axios.get(this.platformInterestURL)
          let pkToRow = {}
          for (let row of response.data) {
            pkToRow[row.platform] = row
          }
          for (let platform of this.platforms) {
            let newData = pkToRow[platform.pk]
            if (newData) {
              this.$set(platform, 'interests', remapInterestRecord(newData))
              platform.title_count = newData.title_count
            } else {
              platform.interests = createEmptyInterestRecord()
              platform.title_count = null
            }
          }
        } catch (error) {
          this.showSnackbar({content: 'Error loading platform details: '+error, color: 'warning'})
        }
      },
      async loadPlatformSushiCounts () {
        if (this.selectedOrganizationId) {
          try {
            let response = await axios.get(`/api/organization/${this.selectedOrganizationId}/sushi-credentials-count/`)
            let pkToCount = {}
            for (let rec of response.data) {
              pkToCount[rec.pk] = rec.count
            }
            for (let platform of this.platforms) {
              this.$set(platform, 'sushi_credentials_count', pkToCount[platform.pk])
            }
          } catch (error) {
              this.showSnackbar({content: 'Error loading platforms: '+error})
          }
        }
      },
    },
    created () {
      this.loadPlatforms()
    },
    watch: {
      selectedOrganizationId () {
        this.loadPlatforms()
      },
      dateRangeStart () {
        this.loadPlatforms()
      },
      dateRangeEnd () {
        this.loadPlatforms()
      }
    }
  }
</script>

<style lang="scss">
    table.v-table {
        thead {
            th.wrap {
                white-space: normal;
            }
        }
    }

    .subdued {
        color: #888888;
    }

    .v-input.small-checkbox {
        margin-top: 0;

        .v-input__slot {
            margin-bottom: 0 !important;
        }

        label {
            font-size: 0.875rem;
        }
    }

</style>
