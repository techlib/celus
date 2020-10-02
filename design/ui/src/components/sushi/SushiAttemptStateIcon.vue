<i18n lang="yaml" src="@/locales/sushi.yaml" />
<i18n lang="yaml">
en:
  details: Details
  field_timestamp: Time
  field_timestamp_latest: Last attempt
  field_error_code: Error code

cs:
  details: Detaily
  field_timestamp: Čas
  field_timestamp_latest: Poslední pokus
  field_error_code: Chybový kód
</i18n>

<template>
  <span v-if="attemptState">
    <v-tooltip bottom>
      <template v-slot:activator="{ on }">
        <span v-on="on">
          <v-icon v-if="attemptState === stateUntried" color="secondary"
            >far fa-clock</v-icon
          >
          <v-icon v-else-if="attemptState === stateQueued" color="secondary"
            >far fa-pause-circle</v-icon
          >
          <v-icon v-else-if="attemptState === stateSuccess" color="success"
            >far fa-check-circle</v-icon
          >
          <v-icon v-else-if="attemptState === stateEmpty" color="success"
            >far fa-circle</v-icon
          >
          <v-icon v-else-if="attemptState === stateError" color="red lighten-2"
            >fa fa-exclamation-circle</v-icon
          >
          <v-icon v-else color="warning">far fa-question-circle</v-icon>
        </span>
      </template>

      <div>
        <div class="explanation">
          {{ $t(`sushi.state_desc.${attemptState}`) }}
        </div>
        <div v-if="attempt && attemptState !== stateUntried">
          <h4 v-text="$t('details')" class="mt-3"></h4>
          <ul>
            <li>
              <strong>{{
                latest ? $t("field_timestamp_latest") : $t("field_timestamp")
              }}</strong
              >: {{ formatDateTime(attempt.timestamp) }}
            </li>
            <li v-if="attempt.error_code">
              <strong>{{ $t("field_error_code") }}</strong
              >: {{ attempt.error_code }}
            </li>
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
  ATTEMPT_NOT_MADE,
  ATTEMPT_EMPTY_DATA,
} from "@/libs/attempt-state";
import { isoDateTimeFormat } from "@/libs/dates";

export default {
  name: "SushiAttemptStateIcon",

  props: {
    attempt: { required: false },
    // when set to true, this attempt is last of several and the wording should reflect it
    latest: { default: false, type: Boolean },
    forceState: { required: false, default: null, type: String },
  },

  data() {
    return {
      stateQueued: ATTEMPT_QUEUED,
      stateSuccess: ATTEMPT_SUCCESS,
      stateError: ATTEMPT_ERROR,
      stateUntried: ATTEMPT_NOT_MADE,
      stateEmpty: ATTEMPT_EMPTY_DATA,
    };
  },

  computed: {
    attemptState() {
      if (this.forceState) {
        return this.forceState;
      } else if (this.attempt) {
        return this.attempt.state
          ? this.attempt.state
          : attemptState(this.attempt);
      }
      return null;
    },
  },

  methods: {
    formatDateTime(value) {
      if (value) {
        return isoDateTimeFormat(value);
      }
      return "";
    },
  },
};
</script>
