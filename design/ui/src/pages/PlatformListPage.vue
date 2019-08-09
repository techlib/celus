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
    <div>
        <h2>{{ $t('pages.platforms') }}</h2>
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
            <template v-slot:item.url="props">
                <a v-if="props.item.url" :href="props.item.url" target="_blank">{{ props.item.url }}</a>
                <span v-else>-</span>
            </template>
        </v-data-table>
        </v-card>
    </div>
</template>

<script>
  import { mapActions, mapGetters, mapState } from 'vuex'
  import axios  from 'axios'

  export default {
    name: 'PlatformListPage',
    data () {
      return {
        platforms: [],
        search: '',
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
          {
            text: 'URL',
            value: 'url'
          },
        ]
      }
    },
    methods: {
      ...mapActions({
        showSnackbar: 'showSnackbar',
      }),
      loadPlatforms () {
        if (this.selectedOrganizationId) {
          axios.get(this.platformsURL)
            .then(response => {
              this.platforms = response.data
            })
            .catch(error => {
              this.showSnackbar({content: 'Error loading platforms: '+error})
            })
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
