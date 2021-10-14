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
  <span v-if="intentionState">
    <v-tooltip bottom>
      <template v-slot:activator="{ on }">
        <span v-on="on">
          <v-icon :color="icon.color">{{ icon.icon }} fa-fw</v-icon>
          <!-- show additional icon when credentials are broken -->
          <v-icon v-if="brokenCredentials" x-small color="warning" class="pl-1">
            fa-exclamation fa-fw
          </v-icon>
          <v-icon v-else-if="brokenReport" x-small color="warning" class="pl-1">
            fa-exclamation fa-fw
          </v-icon>
        </span>
      </template>

      <div>
        <div class="explanation">
          {{ $t(`sushi.state_desc.${intentionState}`) }}
        </div>
        <div v-if="brokenReport">
          {{ $t("sushi.state_desc.broken_report") }}
        </div>
        <div v-if="brokenCredentials">
          {{ $t("sushi.state_desc.broken") }}
        </div>
        <div
          v-if="
            intention && intention.attempt && intentionState !== stateUntried
          "
        >
          <h4 v-text="$t('details')" class="mt-3"></h4>
          <ul>
            <li v-if="intention.attempt">
              <strong>{{
                latest ? $t("field_timestamp_latest") : $t("field_timestamp")
              }}</strong
              >: {{ formatDateTime(intention.attempt.timestamp) }}
            </li>
            <li v-if="intention.attempt.error_code">
              <strong>{{ $t("field_error_code") }}</strong
              >: {{ intention.attempt.error_code }}
            </li>
          </ul>
        </div>
      </div>
    </v-tooltip>
  </span>
</template>
<script>
import {
  intentionState,
  INTENTION_WAITING,
  intentionStateToIcon,
} from "@/libs/intention-state";
import { isoDateTimeFormat } from "@/libs/dates";

export default {
  name: "SushiFetchIntentionStateIcon",

  props: {
    intention: { required: false },
    // when set to true, this intention is last of several and the wording should reflect it
    latest: { default: false, type: Boolean },
    forceState: { required: false, default: null, type: String },
    brokenReport: { default: false, type: Boolean },
    brokenCredentials: { default: false, type: Boolean },
  },

  data() {
    return {
      stateUntried: INTENTION_WAITING,
    };
  },

  computed: {
    intentionState() {
      if (this.forceState) {
        return this.forceState;
      } else if (this.intention) {
        return this.intention.state
          ? this.intention.state
          : intentionState(this.intention);
      }
      return null;
    },
    icon() {
      return intentionStateToIcon(this.intentionState);
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
