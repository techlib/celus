<i18n src="../locales/common.yaml"></i18n>
<i18n>
en:
    columns:
        id: ID
        name: Name
        provider: Provider
        title_count: Title / database count
        sushi_available: SUSHI active
        notes: " "
    sushi_present: SUSHI is available and active for this platform
    no_sushi: SUSHI is not activated for this platform and selected organization
    annotations_available: There are annotations for this platform and the current date range. Go to the
        platform page for details.
    sushi_for_version: "SUSHI for COUNTER version {version} is available"
    sushi_for_version_outside: "SUSHI not managed by consortium for COUNTER version {version} is available"

cs:
    columns:
        id: ID
        name: Název
        provider: Poskytovatel
        title_count: Počet titulů a databází
        sushi_available: Aktivní SUSHI
        notes: " "
    sushi_present: SUSHI je pro tuto platformu aktivní
    no_sushi: SUSHI není pro tuto platformu a vybranou organizaci aktivní
    annotations_available: Pro tuto platformu a vybrané časové období byly uloženy poznámky.
        Na stránce platformy zjistíte detaily.
    sushi_for_version: "SUSHI pro verzi {version} COUNTERu je k dispozici"
    sushi_for_version_outside: "SUSHI nespravované konsorciem pro verzi {version} COUNTERu je k dispozici"
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
                <AddAnnotationButton @update="refreshAnnotations()" class="ml-2"/>
            </v-col>
        </v-row>
        <v-row>
            <AnnotationsWidget :allow-add="showAdminStuff" ref="annotWidget"/>
        </v-row>
        <v-row>
            <v-col>
                <v-card>
                    <v-card-text>
                        <InterestGroupSelector v-model="activeInterestTypes" ref="IGroups"/>
                        <v-container>
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
                        <template v-for="ig in activeInterestTypes" v-slot:[slotName(ig)]="{item}">
                            <span v-if="item.interests.loading" class="fas fa-spinner fa-spin subdued"></span>
                            <span v-else>
                                {{ formatInteger(item.interests[ig]) }}
                            </span>
                        </template>
                        <template v-slot:item.sushi_credentials_versions="{item}">
                            <v-tooltip bottom v-for="record in item.sushi_credentials_versions" :key="10*record.version+record.outside_consortium">
                                <template v-slot:activator="{ on }">
                                    <span v-on="on" class="mr-3 subdued">{{ record.version }}{{ record.outside_consortium ? '*' : '' }}</span>
                                </template>
                                <template v-if="record.outside_consortium">
                                    <i18n path="sushi_for_version_outside" tag="span">
                                        <template v-slot:version>
                                            {{ record.version }}
                                        </template>
                                    </i18n>
                                </template>
                                <template v-else>
                                    <i18n path="sushi_for_version" tag="span">
                                        <template v-slot:version>
                                            {{ record.version }}
                                        </template>
                                    </i18n>
                                </template>
                            </v-tooltip>
                        </template>
                        <template v-slot:item.annotations="{item}">
                            <v-tooltip bottom v-if="item.annotations">
                                <template v-slot:activator="{ on }">
                                    <v-icon x-small v-on="on">fa-exclamation-triangle</v-icon>
                                </template>
                                <template>
                                    {{ $t('annotations_available') }}
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
  import PlatformSelectionWidget from '../components/PlatformSelectionWidget'
  import {formatInteger} from '../libs/numbers'
  import {
    createEmptyInterestRecord,
    createLoadingInterestRecord,
  } from '../libs/interest'
  import AnnotationsWidget from '../components/AnnotationsWidget'
  import AddAnnotationButton from '../components/AddAnnotationButton'
  import InterestGroupSelector from '../components/InterestGroupSelector'

  export default {
    name: 'PlatformListPage',
    components: {
      PlatformSelectionWidget,
      AnnotationsWidget,
      AddAnnotationButton,
      InterestGroupSelector,
    },
    data () {
      return {
        platforms: [],
        search: '',
        loading: false,
        showUploadDataDialog: false,
        activeInterestTypes: ['title', 'database'],
        annotations: {},
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
          text: this.$t('columns.notes'),
          value: 'annotations',
          sortable: false,
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
        if (this.$refs.IGroups) {
          for (let ig of this.$refs.IGroups.interestGroups) {
            if (this.activeInterestTypes.indexOf(ig.short_name) >= 0) {
              base.push({
                text: ig.name,
                value: 'interests.' + ig.short_name,
                class: 'wrap text-xs-right',
                align: 'right',
              })
            }
          }
        }
        base.push({
            text: this.$i18n.t('columns.sushi_available'),
            value: 'sushi_credentials_versions',
            sortable: false,
          })
        return base
      },
      platformsURL () {
        return `/api/organization/${this.selectedOrganizationId}/platform/?start=${this.dateRangeStart}&end=${this.dateRangeEnd}`
      },
      platformInterestURL () {
        return `/api/organization/${this.selectedOrganizationId}/platform-interest/?start=${this.dateRangeStart}&end=${this.dateRangeEnd}`
      },
      annotationsUrl () {
        let url = `/api/annotations/?start_date=${this.dateRangeStart}&end_date=${this.dateRangeEnd}`
        if (this.organizationSelected) {
          url += `&organization=${this.selectedOrganizationId}`
        }
        return url
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
            this.loadAnnotations()
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
              this.$set(platform, 'interests', newData)
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
            let response = await axios.get(`/api/organization/${this.selectedOrganizationId}/sushi-credentials-versions/`)
            for (let platform of this.platforms) {
              let key = platform.pk.toString()
              if (key in response.data) {
                this.$set(platform, 'sushi_credentials_versions', response.data[key])
              } else {
                this.$set(platform, 'sushi_credentials_versions', {})
              }
            }
          } catch (error) {
              this.showSnackbar({content: 'Error loading platforms: '+error})
          }
        }
      },
      async loadAnnotations () {
        this.annotations = {}
        try {
          let response = await axios.get(this.annotationsUrl)
          this.annotations = {}
          // populate the this.annotations object
          for (let annot of response.data.filter(item => item.platform != null)) {
            if (!(annot.platform.pk in this.annotations)) {
              this.annotations[annot.platform.pk] = []
            }
            this.annotations[annot.platform.pk].push(annot)
          }
          // assign annotations to individual platform
          for (let platform of this.platforms) {
            if (platform.pk in this.annotations) {
              this.$set(platform, 'annotations', this.annotations[platform.pk])
            }
          }
        } catch (error) {
          this.showSnackbar({content: 'Error loading annotations: ' + error, color: 'error'})
        }
      },
      refreshAnnotations () {
        this.$refs.annotWidget.fetchAnnotations()
        this.loadAnnotations()
      },
      slotName (name) {
        return 'item.interests.' + name
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
