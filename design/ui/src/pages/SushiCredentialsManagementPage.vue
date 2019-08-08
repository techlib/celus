<i18n src="../locales/common.yaml"></i18n>

<template>
    <v-layout>
        <v-data-table
                :items="sushiCredentialsList"
                :headers="headers"

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
    </v-layout>
</template>

<script>
  import axios from 'axios'
  import {mapActions} from 'vuex'

  export default {
    name: "SushiCredentialsManagementPage",
    data () {
      return {
        'sushiCredentialsList': [],
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
            text: this.$i18n.t('title_fields.actions'),
            value: '',
            sortable: false,
          },
        ]
      },
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

<style scoped>

</style>
