<i18n src="../locales/common.yaml"></i18n>
<i18n>
en:
    title:
        edit_sushi_credentials: Edit SUSHI credentials

cs:
    title:
        edit_sushi_credentials: Přihlašovací údaje SUSHI
</i18n>


<template>
    <v-layout>
        <v-card>
            <v-card-title>
                <v-spacer></v-spacer>
                <v-text-field
                        v-model="searchDebounced"
                        append-icon="fa-search"
                        :label="$t('labels.search')"
                        single-line
                        hide-details
                        clearable
                        clear-icon="fa-times"
                ></v-text-field>
            </v-card-title>
            <v-data-table
                    :items="sushiCredentialsList"
                    :headers="headers"
                    :search="search"
                    :items-per-page.sync="itemsPerPage"
            >
                <template v-slot:item.active_counter_reports="props">
                    <v-tooltip
                            bottom
                            v-for="(report, index) in props.item.active_counter_reports"
                            :key="index"
                    >
                        <template v-slot:activator="{ on }">
                            <v-chip
                                    class="mr-1"
                                    color="teal"
                                    outlined
                                    label
                                    v-on="on"
                            >
                                {{ report.code }}
                            </v-chip>
                        </template>
                        <span>
                            <span v-if="report.name">{{ report.name }}</span>
                            <span v-else>{{ report.code }}</span>
                        </span>
                    </v-tooltip>
                </template>
                <template v-slot:item.actions="props">
                    <v-btn text small color="secondary" @click.stop="selectedCredentials = props.item; showEditDialog = true">
                        <v-icon left x-small>fa-edit</v-icon>
                        {{ $t('actions.edit') }}
                    </v-btn>
                </template>
                <template v-slot:item.enabled="props">
                    <v-icon x-small>{{ props.item.enabled ? 'fa-check' : 'fa-times' }}</v-icon>
                </template>
            </v-data-table>
        </v-card>
        <v-dialog v-model="showEditDialog">
            <v-card>
                <v-card-title class="headline">{{ $t('title.edit_sushi_credentials') }}</v-card-title>
                <v-card-text>
                    <SushiCredentialsEditDialog
                            :credentials-object="selectedCredentials"
                    ></SushiCredentialsEditDialog>
                </v-card-text>
                <v-card-actions>
                    <v-layout pb-3 pr-5 justify-end>
                    <v-btn color="secondary" @click="showEditDialog = false">Close</v-btn>
                    <v-btn color="primary" @click="showEditDialog = false">Save</v-btn>
                    </v-layout>
                </v-card-actions>
            </v-card>
        </v-dialog>
    </v-layout>
</template>

<script>
  import axios from 'axios'
  import {mapActions} from 'vuex'
  import { debounce } from 'lodash'
  import SushiCredentialsEditDialog from '../components/SushiCredentialsEditDialog'

  export default {
    name: "SushiCredentialsManagementPage",
    components: {SushiCredentialsEditDialog},
    data () {
      return {
        sushiCredentialsList: [],
        search: '',
        itemsPerPage: 25,
        selectedCredentials: null,
        showEditDialog: false,
      }
    },
    computed: {
      headers () {
        return [
          {
            text: this.$i18n.t('organization'),
            value: 'organization.name',
            class: 'wrap',
          },
          {
            text: this.$i18n.t('platform'),
            value: 'platform.name'
          },
          {
            text: this.$i18n.t('title_fields.counter_version'),
            value: 'counter_version',
            align: 'end',
          },
          {
            text: this.$i18n.t('title_fields.active_reports'),
            value: 'active_counter_reports',
            sortable: false,
          },
          {
            text: this.$i18n.t('title_fields.enabled'),
            value: 'enabled',
          },
          {
            text: this.$i18n.t('title_fields.actions'),
            value: 'actions',
            sortable: false,
          },
        ]
      },
      searchDebounced: {
        get () {
          return this.search
        },
        set: debounce(function (value) {
          this.search = value
        }, 500)
      }
    },
    methods: {
      ...mapActions({
        showSnackbar: 'showSnackbar',
      }),
      async loadSushiCredentialsList () {
        try {
          let response = await axios.get('/api/sushi-credentials/')
          this.sushiCredentialsList = response.data
        } catch (error) {
          this.showSnackbar({content: 'Error loading credentials list: '+error})
        }

      }
    },
    mounted() {
      this.loadSushiCredentialsList()
    }
  }
</script>

<style lang="scss">
</style>
