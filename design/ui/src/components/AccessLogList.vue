<i18n src="../locales/common.yaml"></i18n>

<template>
    <v-data-table
            :items="accessLogs"
            :headers="headers"
            :sort-by.sync="orderBy"
            :loading="loading"
            dense
    >
    </v-data-table>
</template>

<script>
  import axios from 'axios'
  import {mapActions} from 'vuex'
  export default {
    name: "AccessLogList",
    props: {
      importBatch: {required: false},
      organization: {required: false},
      platform: {required: false},
      title: {required: false},
    },
    data () {
      return {
        accessLogs: [],
        orderBy: ['date', 'target'],
        loading: false,
      }
    },
    computed: {
      headers() {
        return [
          {
            text: this.$i18n.t('labels.date'),
            value: 'date'
          },
          {
            text: this.$i18n.t('labels.title'),
            value: 'target'
          },
          ...this.dynamicHeaders,
          {
            text: this.$i18n.t('labels.metric'),
            value: 'metric'
          },
          {
            text: this.$i18n.t('labels.value'),
            value: 'value',
          },
        ]
      },
      dynamicHeaders () {
        let headers = []
        if (this.accessLogs.length > 0) {
          for (let key of Object.keys(this.accessLogs[0])) {
            if (key !== 'date' && key !== 'metric' && key !== 'value' && key !== 'organization' &&
                key !== 'platform' && key !== 'report_type' && key !== 'target' && key !== 'row') {
              headers.push({text: key.replace(/_/g, ' '), value: key})
            }
          }
        }
        return headers
      }
    },
    methods: {
      ...mapActions({
        showSnackbar: 'showSnackbar',
      }),
      async loadLogs () {
        this.loading = true
        let params = {format: 'json'}
        if (this.importBatch) {
          params['import_batch'] = this.importBatch
        }
        if (this.organization) {
          params['organization'] = this.organization
        }
        if (this.platform) {
          params['platform'] = this.platform
        }
        if (this.title) {
          params['target'] = this.title
        }
        try {
          let response = await axios.get('/api/raw-data/', {params: params})
          this.accessLogs = response.data
        } catch (error) {
          this.showSnackbar({content: 'Error loading data: ' + error})
        } finally {
          this.loading = false
        }
      }
    },
    watch: {
      importBatch () {
        this.accessLogs = []
        this.loadLogs()
      }
    },
    mounted () {
      this.loadLogs()
    }
  }
</script>

<style scoped>

</style>
