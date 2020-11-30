<i18n lang="yaml" src="@/locales/sushi.yaml" />

<template>
  <v-tooltip bottom>
    <template #activator="{ on }">
      <span v-on="on">
        <v-icon :color="icon.color">{{ icon.icon }} fa-fw</v-icon>
      </span>
    </template>
    {{ $t("sushi.state_desc." + fetchIntention.state) }}
  </v-tooltip>
</template>

<script>
import { intentionStateToIcon } from "@/libs/intention-state";

export default {
  name: "FetchIntentionStatusIcon",

  props: {
    fetchIntention: {
      required: true,
      type: Object,
    },
  },

  computed: {
    icon() {
      return intentionStateToIcon(this.fetchIntention.state);
    },
  },
};
</script>
