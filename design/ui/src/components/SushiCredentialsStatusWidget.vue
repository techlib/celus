<i18n src="../locales/common.yaml"></i18n>
<i18n>
en:
    in_progress: Fetching data
    fetching_details: Fetching details
    no_data_yet: There are no data yet, please wait until the download finishes. It can take from seconds to minutes.

cs:
    in_progress: Stahuji data
    fetching_details: Stahuji informace
    no_data_yet: Data ještě nejsou k dispozici - vyčkejte prosím, až budou stáhnutá. Může to trvat od sekund po jednotky minut.
</i18n>
<template>
    <v-expansion-panel>
        <v-expansion-panel-header v-slot="{ open }">
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
                        <strong v-text="attemptData.counter_report_verbose.code"></strong>
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
            <v-row v-else>
                <v-col cols="auto">
                    <strong v-text="attemptData.counter_report_verbose.code"></strong>
                </v-col>
                <v-col>
                    {{ $t('title_fields.download_success') }}:
                    <CheckMark :value="attemptData.download_success" extra-classes="fa-fw"></CheckMark>
                    {{ $t('title_fields.processing_success') }}:
                    <CheckMark :value="attemptData.processing_success" extra-classes="fa-fw"></CheckMark>
                    {{ $t('title_fields.contains_data') }}:
                    <CheckMark :value="attemptData.contains_data" extra-classes="fa-fw"></CheckMark>
                </v-col>
            </v-row>
        </v-expansion-panel-header>
        <v-expansion-panel-content>
            <span v-if="!attemptData || attemptData.in_progress" v-text="$t('no_data_yet')"></span>
            <div v-else>
                <div v-if="attemptData.data_file">
                    <strong>{{ $t('title_fields.data_file')}}</strong>:
                    <a :href="attemptData.data_file" target="_blank">{{ attemptData.data_file }}</a>
                </div>
                <div v-if="attemptData.error_code">
                    <strong>{{ $t('title_fields.error_code') }}</strong>: {{ attemptData.error_code }}
                </div>
                <div v-if="attemptData.log">
                    <strong>{{ $t('title_fields.log') }}</strong>: {{ attemptData.log }}
                </div>
            </div>
        </v-expansion-panel-content>
    </v-expansion-panel>
</template>

<script>
  import { mapActions } from 'vuex'
  import axios from 'axios'
  import CheckMark from './CheckMark'

  export default {
    name: 'SushiCredentialsStatusWidget',
    components: {CheckMark},
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
