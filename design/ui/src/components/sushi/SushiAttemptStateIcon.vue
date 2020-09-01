<i18n lang="yaml">
en:
  attempt_state_unknown: The state is not clear. There was not obvious error but no data were imported.
  attempt_state_queued: Data was not yet available so future attempts were queued.
  attempt_state_error: There was an error downloading data.
  attempt_state_success: Data were successfully downloaded and ingested into Celus.
  attempt_state_missing: Data retrieval was not yet performed.
  details: Details
  field_timestamp: Last attempt
  field_error_code: Error code

cs:
  attempt_state_unknown: Stav není jednoznačný. Nedošlo ke zjevné chybě, ale import neobsahoval žádná data.
  attempt_state_queued: Data zatím nebyla k dispozici, bylo naplánováno další stažení v budoucnosti.
  attempt_state_error: Došlo k chybě při stahování dat.
  attempt_state_success: Data byla úspěšně stažená a uložená v systému.
  attempt_state_missing: Stažení dat zatím nebylo provedeno.
  details: Detaily
  field_timestamp: Poslední pokus
  field_error_code: Chybový kód
</i18n>

<template>
    <span v-if="attemptState">
        <v-tooltip bottom>
            <template v-slot:activator="{ on }">
                <span v-on="on" >
                    <v-icon v-if="attemptState === stateUntried" color="secondary">far fa-clock</v-icon>
                    <v-icon v-else-if="attemptState === stateQueued" color="secondary">far fa-pause-circle</v-icon>
                    <v-icon v-else-if="attemptState === stateSuccess" color="success">far fa-check-circle</v-icon>
                    <v-icon v-else-if="attemptState === stateError" color="red lighten-2">fa fa-exclamation-circle</v-icon>
                    <v-icon v-else color="warning">far fa-question-circle</v-icon>
                </span>
            </template>

            <div>
                <div class="explanation">
                    {{ $t(`attempt_state_${attemptState}`) }}
                </div>
                <div v-if="attempt && attemptState !== stateUntried">
                    <h4 v-text="$t('details')" class="mt-3"></h4>
                    <ul>
                        <li><strong>{{ $t('field_timestamp') }}</strong>: {{ formatDateTime(attempt.timestamp) }}</li>
                        <li v-if="attempt.error_code"><strong>{{ $t('field_error_code') }}</strong>: {{ attempt.error_code }}</li>
                    </ul>
                </div>
            </div>
        </v-tooltip>
    </span>
</template>
<script>
import {
  attemptState,
  ATTEMPT_QUEUED,
  ATTEMPT_SUCCESS,
  ATTEMPT_ERROR,
  ATTEMPT_NOT_MADE
} from '@/libs/attempt-state'
import { parseDateTime, isoDateTimeFormat } from '@/libs/dates'

export default {
  name: 'SushiAttemptStateIcon',

  props: {
    attempt: {required: false},
    forceState: {required: false, default: null, type: String}
  },

  data () {
    return {
      stateQueued: ATTEMPT_QUEUED,
      stateSuccess: ATTEMPT_SUCCESS,
      stateError: ATTEMPT_ERROR,
      stateUntried: ATTEMPT_NOT_MADE,
    }
  },

  computed: {
    attemptState () {
      if (this.forceState) {
        return this.forceState
      } else if (this.attempt) {
        return attemptState(this.attempt)
      }
      return null
    }
  },

  methods: {
    formatDateTime (value) {
      let date = parseDateTime(value)
      if (date) {
        return isoDateTimeFormat(date)
      }
      return ''
    }
  }
}
</script>
