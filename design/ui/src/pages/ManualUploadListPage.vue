<template>
    <v-container fluid>
        <v-row>
            <v-col>
                <h2>Manual uploads</h2>
            </v-col>
        </v-row>
        <v-row>
            <v-col>
                <ManualUploadListTable />
            </v-col>
        </v-row>
    </v-container>
</template>

<script>
  import ManualUploadListTable from '../components/ManualUploadListTable'
  import { mapGetters } from 'vuex'

  export default {
    name: "ManualUploadListPage",

    components: {
      ManualUploadListTable
    },

    computed: {
      ...mapGetters({
        organizationSelected: 'organizationSelected',
      })
    }

  }
</script>

<style scoped>

</style>
