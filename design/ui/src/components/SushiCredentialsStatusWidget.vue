<i18n>
en:
    in_progress: Fetching data
    fetching_details: Fetching details

cs:
    in_progress: Stahuji data
    fetching_details: Stahuji informace
</i18n>
<template>
    <div>
        <v-progress-linear
                v-if="attemptData === null"
                height="1.5rem"
                indeterminate
        >
            <span v-text="$t('fetching_details')"></span>
        </v-progress-linear>
        <v-row
                v-else-if="attemptData.in_progress"
        >
            <v-col cols="auto">
                <span v-text="attemptData.counter_report_verbose.code"></span>
            </v-col>
            <v-col>
            <v-progress-linear

                    height="1.5rem"
                    indeterminate
            >
                <span>{{ $t('in_progress') }}, {{ elapsedTime }} s</span>
            </v-progress-linear>
            </v-col>
            </v-row>
        <div v-else>
            <span v-text="attemptData.counter_report_verbose.code"></span>: <span v-text="attemptData.download_success"></span>
        </div>
    </div>
</template>

<script>
  import { mapActions } from 'vuex'
  import axios from 'axios'

  export default {
    name: 'SushiCredentialsStatusWidget',
    props: {
      attemptId: {
        required: true,
        type: Number,
      }
    },
    data () {
      return {
        attemptData: null,
        startTime: null,
        now: null,
        retryInterval: 1000,
        lastCheck: null,
        inactive: false,
      }
    },
    computed: {
      elapsedTime () {
        return Math.round((this.now - this.startTime) / 1000)
      }
    },
    methods: {
      ...mapActions({
        showSnackbar: 'showSnackbar',
      }),
      async check () {
        try {
          let response = await axios.get(`/api/sushi-fetch-attempt/${this.attemptId}/`)
          this.attemptData = response.data
          if (this.attemptData.in_progress && !this.inactive) {
            setTimeout(this.check, this.retryInterval)
          }
        } catch (error) {
          this.showSnackbar({content: 'Error checking SUSHI attemps: ' + error, color: 'error'})
        }
      },
      stop () {
        console.log('clean')
        this.inactive = true
      }
    },
    mounted () {
      this.startTime = (new Date()).getTime()
      this.check()
      setInterval(() => {this.now = (new Date()).getTime()}, 200)
    },
    beforeDestroy () {
      this.inactive = true
    }
  }
</script>

<style scoped>

</style>
