<i18n src="../locales/common.yaml"></i18n>
<i18n>
en:
    columns:
        id: ID
        name: Name
        provider: Provider
        title_count: Title count
        interest: Interest
        rel_interest: Int. / title
cs:
    columns:
        id: ID
        name: Název
        provider: Poskytovatel
        title_count: Počet titulů
        interest: Zájem
        rel_interest: Zájem / titul
</i18n>

<template>
    <div>
        <h2>{{ $t('pages.platforms') }}</h2>
        <v-data-table
                :items="platforms"
                :headers="headers"
                :hide-actions="true"
        >
            <template v-slot:items="props">
                <td class="text-xs-right">{{ props.item.pk }}</td>
                <td><router-link :to="{name: 'platform-detail', params: {platformId: props.item.pk}}">{{ props.item.name }}</router-link></td>
                <td class="text-xs-right">{{ props.item.title_count }}</td>
                <td class="text-xs-right">{{ props.item.interest }}</td>
                <td class="text-xs-right">{{ formatNumber(props.item.rel_interest) }}</td>
                <td>{{ props.item.provider }}</td>
                <td>
                    <a v-if="props.item.url" :href="props.item.url" target="_blank">{{ props.item.url }}</a>
                    <span v-else>-</span>
                </td>
            </template>
        </v-data-table>
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
        headers: [
          {
            text: this.$i18n.t('columns.id'),
            value: 'pk'
          },
          {
            text: this.$i18n.t('columns.name'),
            value: 'name'
          },
          {
            text: this.$i18n.t('columns.title_count'),
            value: 'title_count'
          },
          {
            text: this.$i18n.t('columns.interest'),
            value: 'interest'
          },
          {
            text: this.$i18n.t('columns.rel_interest'),
            value: 'rel_interest'
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

<style scoped>

</style>
