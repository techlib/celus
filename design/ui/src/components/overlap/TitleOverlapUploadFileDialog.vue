<i18n src="@/locales/common.yaml" lang="yaml"></i18n>
<i18n lang="yaml">
en:
  upload_csv_file: Upload CSV file with titles
  dialog_intro: |
    Upload a CSV file containing one title per line. The file should contain at least one
    of the following columns - ISBN, ISSN and eISSN. If unsure how to prepare the file, please have a look at
    <a href="https://support.celus.net/support/solutions/articles/103000062844" target="_blank">
    knowledgebase entry</a>.

cs:
  upload_csv_file: Nahrajte soubor CSV s tituly
  dialog_intro: |
    Nahrajte CSV soubor s jedním titulem na řádek. Soubor by měl obsahovat alespoň jeden
    z následujících sloupců - ISBN, ISSN a eISSN. Pokud nevíte, jak soubor připravit, podívejte se na
    <a href="https://support.celus.net/support/solutions/articles/103000062844" target="_blank">
    tento návod</a>.
</i18n>

<template>
  <v-dialog v-model="show" max-width="640px">
    <v-card class="py-2 px-1">
      <v-card-title>
        {{ $t("actions.upload_file_for_annotation") }}
      </v-card-title>
      <v-card-text>
        <v-row>
          <v-col>
            <div v-html="$t('dialog_intro')"></div>
          </v-col>
        </v-row>
        <v-row>
          <v-col>
            <v-file-input
              :label="$t('upload_csv_file')"
              prepend-icon="fa-list-alt"
              v-model="dataFile"
              show-size
            ></v-file-input>
          </v-col>
          <v-col cols="auto" class="align-self-center">
            <v-btn color="primary" @click="uploadFile" :disabled="!dataFile">
              {{ $t("actions.upload_file") }}
            </v-btn>
          </v-col>
        </v-row>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn color="secondary" @click="show = false">
          {{ $t("actions.cancel") }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
export default {
  name: "TitleOverlapUploadFileDialog",

  props: {
    value: { type: Boolean, default: false },
  },

  data() {
    return {
      show: this.value,
      dataFile: null,
    };
  },

  methods: {
    uploadFile() {
      this.$emit("upload-file", this.dataFile);
    },
  },

  watch: {
    value() {
      this.show = this.value;
    },
    show() {
      this.$emit("input", this.show);
    },
  },
};
</script>

<style scoped lang="scss"></style>
