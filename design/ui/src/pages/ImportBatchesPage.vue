<i18n src="../locales/common.yaml"></i18n>

<template>
    <v-data-table
            :items="batches"
            :headers="headers"
    >
    </v-data-table>

</template>

<script>

  import axios from 'axios'

  export default {
    name: "ImportBatchesPage",
    data () {
      return {
        batches: [],
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
            text: this.$i18n.t('labels.user'),
            value: 'user',
          },
        ]
      }
    },
    methods: {
      async loadImportBatches () {
        let response = await axios.get('/api/import-batch/')
        this.batches = response.data.results
      }
    },
    mounted () {
      this.loadImportBatches()
    }
  }
</script>

<style scoped>

</style>
