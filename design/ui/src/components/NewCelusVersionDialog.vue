<i18n lang="yaml">
en:
  title: New Celus version available
  text: "Celus is being updated ({oldVersion} -> {newCelusVersion})."
  wait:  Wait a moment, please...
  button: Update now
cs:
  title: Je dostupná nová verze Celusu
  text: "Celus se aktualizuje ({oldVersion} -> {newCelusVersion})."
  wait: Mějte prosím chvilku strpení...
  button: Aktualizovat hned
</i18n>

<template>
  <v-dialog
    v-model="newCelusVersion"
    persistent
    :max-width="350"
  >
    <v-card>
      <v-card-title class="headline">{{ $t("title") }}<v-spacer/></v-card-title>
      <v-card-text>
        <div>{{ $t("text", {newCelusVersion: newCelusVersion, oldVersion: oldVersion}) }}</div>
        <br/>
        <div>{{ $t("wait") }} <v-icon color="info">fa-cog fa-spin</v-icon></div>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn
          color="primary"
          class="ma-3"
          @click="refreshPage"
          v-text="$t('button')"
        ></v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
<script>
import { mapGetters, mapState } from "vuex";

export default {
  name: "NewCelusVersionDialog",
  props: {},
  data() {
    return {};
  },

  computed: {
    ...mapGetters({
      oldVersion: "celusVersion",
    }),
    ...mapState({
      newCelusVersion: (state) => state.newCelusVersion,
    }),
  },

  methods: {
    refreshPage() {
      window.location.reload()
    },
  },

  watch: {},
  mounted() {
    // Refresh current page in 10 seconds
    setTimeout(this.refreshPage, 10000);
  }
};
</script>
<style lang="scss">
.v-select.v-text-field.short input {
  max-width: 0;
}

div.small {
  font-size: 80%;
}
</style>
