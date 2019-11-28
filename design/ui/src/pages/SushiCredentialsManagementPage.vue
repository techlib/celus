<i18n lang="yaml" src="../locales/common.yaml"></i18n>
<i18n lang="yaml">
en:
    add_new: Add new SUSHI
    is_locked: These credentials are locked.
    is_unlocked: These credentials are not locked, you may edit them.
    cannot_edit: You cannot edit them.
    can_edit: Because of your priviledges, you can still edit them.
    can_lock: You may lock/unlock these credentials - click to do so.
cs:
    add_new: Přidat nové SUSHI
    is_locked: Tyto přístupové údaje jsou uzamčené.
    is_unlocked: Tyto přístupové údaje nejsou uzamčené, můžete je editovat
    cannot_edit: Nemůžete je editovat.
    can_edit: Vaše oprávnění Vám umožňují je přesto editovat.
    can_lock: Kliknutím můžete tyto údaje uzamknout/odemknout.
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
                    :loading="loading"
            >
                <template v-slot:item.active_counter_reports="{item}">
                    <v-tooltip
                            bottom
                            v-for="(report, index) in item.active_counter_reports_long"
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
                <template v-slot:item.actions="{item}">
                    <v-btn v-if="!item.locked_for_me" text small color="secondary" @click.stop="selectedCredentials = item; showEditDialog = true">
                        <v-icon left x-small>fa-edit</v-icon>
                        {{ $t('actions.edit') }}
                    </v-btn>
                    <v-btn text small color="secondary" @click.stop="selectedCredentials = item; showDetailsDialog = true">
                        <v-icon left x-small>fa-list</v-icon>
                        {{ $t('actions.show_attempts') }}
                    </v-btn>
                </template>
                <template v-slot:item.enabled="{item}">
                    <CheckMark :value="item.enabled" />
                </template>
                <template v-slot:item.outside_consortium="{item}">
                    <CheckMark :value="item.outside_consortium" />
                </template>
                <template v-slot:item.locked="{item}">
                    <!-- locked for me -->
                    <v-tooltip bottom v-if="item.locked && item.locked_for_me">
                        <template v-slot:activator="{ on }">
                            <v-icon small v-on="on" color="red">fa-fw fa-lock</v-icon>
                        </template>
                        {{ $t('is_locked') }} {{ $t('cannot_edit') }}
                    </v-tooltip>
                    <!-- locked, but I can edit -->
                    <v-tooltip bottom v-else-if="item.locked">
                        <template v-slot:activator="{ on }">
                            <v-icon small v-on="on" color="red">fa-fw fa-lock</v-icon>
                        </template>
                        {{ $t('is_locked') }} {{ $t('can_edit') }}
                    </v-tooltip>
                    <!-- not locked at all -->
                    <v-tooltip bottom v-else>
                        <template v-slot:activator="{ on }">
                            <v-icon small v-on="on" color="green">fa-fw fa-lock-open</v-icon>
                        </template>
                        {{ $t('is_unlocked') }}
                    </v-tooltip>

                    <v-tooltip bottom v-if="item.can_lock">
                        <template v-slot:activator="{ on }">
                            <v-btn text icon @click="toggleLock(item)" v-on="on"><v-icon small>fa-key</v-icon></v-btn>
                        </template>
                        {{ $t('can_lock') }}
                    </v-tooltip>
                </template>
            </v-data-table>
        </v-card>
        <v-dialog v-model="showEditDialog">
            <SushiCredentialsEditDialog
                    :credentials-object="selectedCredentials"
                    v-model="showEditDialog"
                    @update-credentials="updateCredentials"
                    @deleted="deleteCredentials"
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
  import CheckMark from '../components/CheckMark'

  export default {
    name: "SushiCredentialsManagementPage",
    components: {SushiCredentialsEditDialog, SushiAttemptListWidget, CheckMark},
    data () {
      return {
        sushiCredentialsList: [],
        search: '',
        itemsPerPage: 25,
        selectedCredentials: null,
        showEditDialog: false,
        showDetailsDialog: false,
        showCreateDialog: false,
        orderBy: ['organization.name', 'platform.name', 'counter_version'],
        loading: false,
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
            text: this.$i18n.t('title_fields.outside_consortium'),
            value: 'outside_consortium',
          },
          {
            text: this.$i18n.t('title_fields.enabled'),
            value: 'enabled',
          },
          {
            text: this.$i18n.t('title_fields.lock'),
            value: 'locked',
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
        this.loading = true
        try {
          let response = await axios.get(`/api/sushi-credentials/?organization=${this.organizationId}`)
          this.sushiCredentialsList = response.data
        } catch (error) {
          this.showSnackbar({content: 'Error loading credentials list: '+error})
        } finally {
          this.loading = false
        }

      },
      updateCredentials (credentials) {
        // the new credentials as returned by the edit dialog
        // we put them at the right place in the list of credentials
        let found = false
        for (let i=0; i < this.sushiCredentialsList.length; i++) {
          if (this.sushiCredentialsList[i].pk === credentials.pk) {
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
      deleteCredentials ({id}) {
        this.sushiCredentialsList = this.sushiCredentialsList.filter(item => item.pk !== id)
      },
      async toggleLock (credentials) {
        let newLockLevel = 400
        if (credentials.locked) {
          newLockLevel = 300
        }
        try {
          let response = await axios.post(`/api/sushi-credentials/${credentials.pk}/lock/`,
            {lock_level: newLockLevel})
          credentials.lock_level = response.data.lock_level
          credentials.locked = response.data.locked
        } catch (error) {
          this.showSnackbar({content: 'Error (un)locking credentials: '+error, color: 'error'})
        }
      },
      closeDetailsDialog () {
        this.selectedCredentials = null
        this.showDetailsDialog = false
      },
      activateCreateDialog () {
        this.showCreateDialog = true
      },
    },
    watch: {
      showEditDialog (value) {
        if (!value) {
          this.selectedCredentials = null
        }
      },
      showCreateDialog (value) {
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
