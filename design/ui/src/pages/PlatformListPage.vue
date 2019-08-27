<i18n src="../locales/common.yaml"></i18n>
<i18n>
en:
    columns:
        id: ID
        name: Name
        provider: Provider
        title_count: Title / database count
        interest: Interest
        rel_interest: Int. / title
cs:
    columns:
        id: ID
        name: Název
        provider: Poskytovatel
        title_count: Počet titulů a databází
        interest: Zájem
        rel_interest: Zájem / titul
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
                    <v-card-title>
                        <v-spacer></v-spacer>
                        <v-text-field
                                v-model="search"
                                append-icon="fa-search"
                                :label="$t('labels.search')"
                                single-line
                                hide-details
                        ></v-text-field>
                    </v-card-title>
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
                        <template v-slot:item.interests.title="props">
                            {{ props.item.interests.title ? props.item.interests.title.value : '-' }}
                        </template>
                        <template v-slot:item.interests.database.value="props">
                            {{ props.item.interests.database ? props.item.interests.database.value : '-' }}
                        </template>
                    </v-data-table>
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

  export default {
    name: 'PlatformListPage',
    components: {PlatformSelectionWidget},
    data () {
      return {
        platforms: [],
        search: '',
        loading: false,
        showUploadDataDialog: false,
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
      platformsURL () {
        return `/api/organization/${this.selectedOrganizationId}/detailed-platform/?start=${this.dateRangeStart}&end=${this.dateRangeEnd}`
      },
      headers () {
        return [
          {
            text: this.$i18n.t('columns.name'),
            value: 'name'
          },
          {
            text: this.$i18n.t('columns.title_count'),
            value: 'title_count',
            class: 'wrap',
            align: 'right',
          },
          {
            text: this.$i18n.t('interests.title'),
            value: 'interests.title.value',
            class: 'wrap text-xs-right',
            align: 'right',
          },
          {
            text: this.$i18n.t('interests.database'),
            value: 'interests.database.value',
            class: 'wrap text-xs-right',
            align: 'right',
          },
          {
            text: this.$i18n.t('columns.provider'),
            value: 'provider'
          },
        ]
      }
    },
    methods: {
      ...mapActions({
        showSnackbar: 'showSnackbar',
      }),
      async loadPlatforms () {
        if (this.selectedOrganizationId) {
          this.loading = true
          try {
            let response = await axios.get(this.platformsURL)
            this.platforms = response.data
          } catch (error) {
              this.showSnackbar({content: 'Error loading platforms: '+error})
          } finally {
            this.loading = false
          }
        }
      }
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
</style>
