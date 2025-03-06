<i18n lang="yaml">
en:
  title: New CELUS version available
  text: "CELUS is being updated ({oldVersion} -> {newCelusVersion})."
  wait: Wait a moment, please...
  button: Update now
cs:
  title: Je dostupná nová verze CELUSu
  text: "CELUS se aktualizuje ({oldVersion} -> {newCelusVersion})."
  wait: Mějte prosím chvilku strpení...
  button: Aktualizovat hned
</i18n>

<template>
  <v-dialog v-model="newCelusVersion" persistent :max-width="400">
    <v-card>
      <v-card-title class="headline"
        >{{ $t("title") }}<v-spacer></v-spacer
      ></v-card-title>
      <v-card-text>
        <div>
          {{
            $t("text", {
              newCelusVersion: newCelusVersion,
              oldVersion: oldVersion,
            })
          }}
        </div>
        <br />
        <div>
          {{ $t("wait") }} <v-icon color="info">fa fa-cog fa-spin</v-icon>
        </div>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn color="primary" class="ma-3" @click="refreshPage">{{
          $t("button")
        }}</v-btn>
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
      window.location.reload();
    },
  },

  watch: {},
  mounted() {
    // Refresh current page in 10 seconds
    setTimeout(this.refreshPage, 10000);
  },
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
