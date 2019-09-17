<i18n src="../locales/common.yaml"></i18n>
<i18n>
en:
    add_new: Add new SUSHI

cs:
    add_new: Přidat nové SUSHI
</i18n>

<template>
    <v-layout>
        <v-card>
            <v-card-title>
                <v-btn
                        @click="activateCreateDialog()"
                        color="warning"
                >
                    <v-icon small class="mr-2">fa-plus</v-icon>
                    {{ $t('add_new') }}
                </v-btn>
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
                    :sort-by="orderBy"
                    multi-sort
                    :footer-props="{itemsPerPageOptions: [10, 25, 50, 100]}"
            >
                <template v-slot:item.active_counter_reports="props">
                    <v-tooltip
                            bottom
                            v-for="(report, index) in props.item.active_counter_reports_long"
                            :key="index"
                    >
                        <template v-slot:activator="{ on }">
                            <v-chip class="mr-1" color="teal" outlined label v-on="on">
                                {{ report.code }}
                            </v-chip>
                        </template>
                        <span>
                            <span v-if="report.name">{{ report.name }}</span>
                            <span v-else>{{ report.code }}</span>
                        </span>
                    </v-tooltip>
                </template>
                <template v-slot:item.actions="props
">
                    <v-btn text small color="secondary" @click.stop="selectedCredentials = props.item; showEditDialog = true">
                        <v-icon left x-small>fa-edit</v-icon>
                        {{ $t('actions.edit') }}
                    </v-btn>
                    <v-btn text small color="secondary" @click.stop="selectedCredentials = props.item; showDetailsDialog = true">
                        <v-icon left x-small>fa-list</v-icon>
                        {{ $t('actions.show_attempts') }}
                    </v-btn>
                </template>
                <template v-slot:item.enabled="props">
                    <v-icon x-small>{{ props.item.enabled ? 'fa-check' : 'fa-times' }}</v-icon>
                </template>
            </v-data-table>
        </v-card>
        <v-dialog v-model="showEditDialog">
            <SushiCredentialsEditDialog
                    :credentials-object="selectedCredentials"
                    v-model="showEditDialog"
                    @update-credentials="updateCredentials"
                    key="edit"
            ></SushiCredentialsEditDialog>
        </v-dialog>
        <v-dialog v-model="showCreateDialog">
            <SushiCredentialsEditDialog
                    v-model="showCreateDialog"
                    @update-credentials="updateCredentials"
                    :existing-credentials="sushiCredentialsList"
                    key="create"
            ></SushiCredentialsEditDialog>
        </v-dialog>
        <v-dialog v-model="showDetailsDialog">
            <SushiAttemptListWidget
                    v-if="selectedCredentials"
                    :organization="selectedCredentials.organization"
                    :platform="selectedCredentials.platform"
                    :counter-version="selectedCredentials.counter_version"
                    @close="closeDetailsDialog"
            >
            </SushiAttemptListWidget>
        </v-dialog>
    </v-layout>
</template>

<script>
  import axios from 'axios'
  import { mapActions, mapState } from 'vuex'
  import debounce from 'lodash/debounce'
  import SushiCredentialsEditDialog from '../components/SushiCredentialsEditDialog'
  import SushiAttemptListWidget from '../components/SushiAttemptListWidget'

  export default {
    name: "SushiCredentialsManagementPage",
    components: {SushiCredentialsEditDialog, SushiAttemptListWidget},
    data () {
      return {
        sushiCredentialsList: [],
        search: '',
        itemsPerPage: 25,
        selectedCredentials: null,
        showEditDialog: false,
        showDetailsDialog: false,
        showCreateDialog: false,
        orderBy: ['organization.name', 'platform.name', 'counter_version']
      }
    },
    computed: {
      ...mapState({
        organizationId: 'selectedOrganizationId',
      }),
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
          let response = await axios.get(`/api/sushi-credentials/?organization=${this.organizationId}`)
          this.sushiCredentialsList = response.data
        } catch (error) {
          this.showSnackbar({content: 'Error loading credentials list: '+error})
        }

      },
      updateCredentials (credentials) {
        // the new credentials as returned by the edit dialog
        // we put them at the right place in the list of credentials
        let found = false
        for (let i=0; i < this.sushiCredentialsList.length; i++) {
          if (this.sushiCredentialsList[i].id === credentials.id) {
            this.$set(this.sushiCredentialsList, i, credentials)
            found = true
            break
          }
        }
        if (!found) {
          // we did not find the corresponding record - we add it at the end
          this.sushiCredentialsList.push(credentials)
        }
      },
      closeDetailsDialog () {
        this.selectedCredentials = null
        this.showDetailsDialog = false
      },
      activateCreateDialog () {
        this.showCreateDialog = true
      }
    },
    watch: {
      showEditDialog (value) {
        if (!value) {
          this.selectedCredentials = null
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
