<template>
    <v-container>
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

  export default {
    name: "ManualUploadListPage",

    components: {
      ManualUploadListTable
    },

  }
</script>

<style scoped>

</style>
