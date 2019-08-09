<i18n src="../locales/common.yaml"></i18n>

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
                    :pagination.sync="pagination"
            >
                <template v-slot:items="props">
                    <td>{{ props.item.organization.name }}</td>
                    <td>{{ props.item.platform.name }}</td>
                    <td>
                        <v-chip
                                v-for="(report, index) in props.item.active_counter_reports"
                                class="ma-1"
                                color="teal"
                                text-color="white"
                                :key="index"
                        >
                            <v-avatar left color="white">
                                <span class="teal--text">{{ report.counter_version }}</span>
                            </v-avatar>
                            {{ report.code }}
                        </v-chip>
                    </td>
                    <td>
                        <v-btn flat small color="secondary">
                            <v-icon left>fa-edit</v-icon>
                            {{ $t('edit') }}
                        </v-btn>
                    </td>
                </template>
            </v-data-table>
        </v-card>
    </v-layout>
</template>

<script>
  import axios from 'axios'
  import {mapActions} from 'vuex'
  import { debounce } from 'lodash'

  export default {
    name: "SushiCredentialsManagementPage",
    data () {
      return {
        sushiCredentialsList: [],
        search: '',
        pagination: {
          sortBy: 'name',
          rowsPerPage: 25,
        },
      }
    },
    computed: {
      headers () {
        return [
          {
            text: this.$i18n.t('organization'),
            value: 'organization.name'
          },
          {
            text: this.$i18n.t('platform'),
            value: 'platform.name'
          },
          {
            text: this.$i18n.t('title_fields.active_reports'),
            value: '',
            sortable: false,
          },
          {
            text: this.$i18n.t('title_fields.actions'),
            value: '',
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

    button.v-btn {
        i.fa {
            font-size: 100%;

            &.v-icon--left {
                margin-right: 8px
            }
        }
    }

</style>
