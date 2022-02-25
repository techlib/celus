<i18n lang="yaml">
en:
  manual_data_upload:
    state:
      initial: Generating overview
      preflight: Overview ready
      prefailed: Generating overview failed
      importing: Importing data
      imported: Imported

cs:
  manual_data_upload:
    state:
      initial: Generuji přehled
      preflight: Přehled připraven
      prefailed: Chyba při generování přehledu selhalo
      importing: Importuji data
      imported: Naimportováno
</i18n>

<template>
  <v-tooltip bottom>
    <template v-slot:activator="{ on }">
      <v-icon small :color="color" v-on="on">
        {{ icon }}
      </v-icon>
    </template>
    <span>{{ $t(`manual_data_upload.state.${state}`) }}</span>
  </v-tooltip>
</template>

<script>
export default {
  name: "ManualUploadState",
  props: {
    state: { required: true, type: String },
  },

  computed: {
    color() {
      switch (this.state) {
        case "initial":
        case "importing":
          return "secondary";
        case "failed":
        case "prefailed":
          return "error";
        case "preflight":
          return "primary";
        case "imported":
          return "success";
        default:
          return "";
      }
    },
    icon() {
      switch (this.state) {
        case "initial":
        case "prefailed":
        case "preflight":
          return "fas fa-search";
        case "failed":
        case "importing":
          return "fas fa-cogs";
        case "imported":
          return "fas fa-check";
        default:
          return "";
      }
    },
  },
};
</script>

<style scoped></style>
