<i18n lang="yaml" src="@/locales/pub-types.yaml"></i18n>
<i18n lang="yaml">
en:
  select_pub_type: Title type filter
  revert_selection: Revert selection
</i18n>

<template>
  <div class="d-flex flex-wrap">
    <div
      v-if="showTitle"
      v-text="$t('select_pub_type') + ':'"
      class="font-weight-bold mr-1 pt-1"
    ></div>
    <div class="pr-3 pt-0">
      <v-tooltip bottom>
        <template #activator="{ on }">
          <v-btn icon :color="color" v-on="on" @click="revertSelection()">
            <v-icon small>fa fa-retweet</v-icon>
          </v-btn>
        </template>
        {{ $t("revert_selection") }}
      </v-tooltip>
    </div>
    <div
      v-for="pubType in pubTypes"
      :key="pubType.code"
      class="mr-4 no-messages"
    >
      <v-tooltip bottom :disabled="!iconsOnly">
        <template #activator="{ on }">
          <span v-on="on">
            <v-checkbox
              :value="pubType.code"
              v-model="selectedPubTypes"
              dense
              class="mt-0"
              :color="color"
            >
              <template #label>
                <v-icon
                  small
                  class="ml-1 mr-1"
                  :color="
                    selectedPubTypes.indexOf(pubType.code) >= 0
                      ? 'orange lighten-2'
                      : '#bbbbbb'
                  "
                  >{{ pubType.icon }}
                </v-icon>
                <span v-if="!iconsOnly">{{ $t(pubType.title) }}</span>
              </template>
            </v-checkbox>
          </span>
        </template>
        {{ $t(pubType.title) }}
      </v-tooltip>
    </div>
  </div>
</template>

<script>
import { pubTypes } from "@/libs/pub-types";

export default {
  name: "TitleTypeFilterWidget",

  props: {
    iconsOnly: {
      default: false,
      type: Boolean,
    },
    value: {
      required: true,
    },
    color: {
      default: "info lighten-1",
      type: String,
    },
    showTitle: {
      default: true,
    },
  },

  methods: {
    revertSelection() {
      this.$set(
        this,
        "selectedPubTypes",
        pubTypes
          .map((item) => item.code)
          .filter((item) => this.selectedPubTypes.indexOf(item) === -1)
      );
    },
  },

  data() {
    return {
      pubTypes: pubTypes,
      selectedPubTypes: [...this.value],
    };
  },

  watch: {
    selectedPubTypes() {
      this.$emit("input", this.selectedPubTypes);
    },
  },
};
</script>

<style lang="scss">
.no-messages {
  .v-messages {
    min-height: 2px;
    max-height: 2px;
  }
}
</style>
