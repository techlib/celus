<i18n src="../locales/common.yaml"></i18n>

<template>
    <div>
        <v-card>
            <v-card-title>
                <v-text-field
                        v-model="searchDebounced"
                        append-icon="fa-search"
                        :label="$t('labels.search')"
                        single-line
                        hide-details
                ></v-text-field>
            </v-card-title>
            <v-data-table
                    :items="batches"
                    :headers="headers"
                    :loading="loading"
                    :search="search"
            >
                <!--:server-items-length="totalCount"
                :items-per-page.sync="pageSize"
                :page.sync="page"
                :sort-by.sync="orderBy"
                :sort-desc.sync="orderDesc"-->
                <template #item.actions="{item}">
                    <v-tooltip bottom>
                        <template v-slot:activator="{ on }">
                            <v-btn icon small color="secondary" @click.stop="selectedBatch = item.pk; dialogType = 'data'; showDialog = true" v-on="on">
                                <v-icon small>fa-microscope</v-icon>
                            </v-btn>
                        </template>
                        <span>{{ $t('actions.show_raw_data') }}</span>
                    </v-tooltip>
                    <v-tooltip bottom>
                        <template v-slot:activator="{ on }">
                            <v-btn icon small color="secondary" @click.stop="selectedBatch = item.pk; dialogType = 'chart'; showDialog = true" v-on="on">
                                <v-icon small>fa-chart-bar</v-icon>
                            </v-btn>
                        </template>
                        <span>{{ $t('actions.show_chart') }}</span>
                    </v-tooltip>
                </template>
                <template #item.user.username="{item}">
                    {{ userToString(item.user) }}
                </template>

            </v-data-table>
        </v-card>

    <v-dialog
            v-model="showDialog"
    >
        <v-card>
            <v-card-text>
                <AccessLogList v-if="dialogType === 'data'" :import-batch="selectedBatch" />
                <ImportBatchChart v-else-if="dialogType === 'chart'" :import-batch-id="selectedBatch" />
            </v-card-text>
            <v-card-actions>
                <v-layout pb-3 pr-5 justify-end>
                    <v-btn @click="showDialog = false">{{ $t('actions.close') }}</v-btn>
                </v-layout>
            </v-card-actions>
        </v-card>
    </v-dialog>
    </div>
</template>

<script>

  import axios from 'axios'
  import {mapActions} from 'vuex'
  import AccessLogList from '../components/AccessLogList'
  import ImportBatchChart from '../components/ImportBatchChart'
  import {isoDateTimeFormat, parseDateTime} from '../libs/dates'
  import debounce from 'lodash/debounce'
  import {userToString} from '../libs/user'

  export default {
    name: "ImportBatchesPage",
    components: {ImportBatchChart, AccessLogList},
    data () {
      return {
        batches: [],
        showDialog: false,
        selectedBatch: null,
        loading: false,
        dialogType: 'data',
        totalCount: 0,
        pageSize: 10,
        page: 1,
        orderBy: 'created',
        orderDesc: false,
        search: '',
      }
    },
    computed: {
      headers () {
        return [
          {
            text: this.$i18n.t('title_fields.id'),
            value: 'pk'
          },
          {
            text: this.$i18n.t('labels.date'),
            value: 'created'
          },
          {
            text: this.$i18n.t('organization'),
            value: 'organization'
          },
          {
            text: this.$i18n.t('platform'),
            value: 'platform'
          },
          {
            text: this.$i18n.t('labels.report_type'),
            value: 'report_type'
          },
          {
            text: this.$i18n.t('labels.user'),
            value: 'user.username',
          },
          /*{
            text: this.$i18n.t('labels.accesslog_count'),
            value: 'accesslog_count',
            sortable: false,
          },*/
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
      userToString: userToString,
      async loadImportBatches () {
        this.loading = true
        let url = `/api/import-batch/?page_size=${this.pageSize}&page=${this.page}`
        if (this.orderBy) {
          url += `&order_by=${this.orderBy}&desc=${this.orderDesc}`
        }
        try {
          let response = await axios.get(url)
          // this.totalCount = response.data.count
          this.batches = response.data //.results
          this.batches = this.batches.map(item => {item.created = isoDateTimeFormat(parseDateTime(item.created)); return item})
        } catch (error) {
          this.showSnackbar({content: 'Error loading title: ' + error})
        } finally {
          this.loading = false
        }
      },
    },
    watch: {
      page () {
        this.loadImportBatches()
      },
      pageSize () {
        this.loadImportBatches()
      },
      orderBy () {
        this.loadImportBatches()
      },
      orderDesc () {
        this.loadImportBatches()
      }
    },
    mounted () {
      this.loadImportBatches()
    }
  }
</script>

<style scoped>

</style>
