<i18n lang="yaml">
en:
  title: Update selection
  texts:
    all_selected: You have selected all records ({count}).
    all_on_page_selected: You have selected all records on the page ({count}).
    some_selected: You have selected some records ({count}).
    none_selected: You haven't selected any records yet.
  actions:
    select_all: Select All ({count})
    select_all_on_page: Select All On page ({count})
    deselect: Deselect All
    cancel: Cancel

cs:
  title: Aktualizovat výběr
  texts:
    all_selected: Máte označeny všechny záznamy ({count}).
    all_on_page_selected: Máte označeny všechny záznamy, které vidíte na stránce ({count}).
    some_selected: Máte označeny část záznamů ({count}).
    none_selected: Zatím nemáte označeny žádné záznamy.
  actions:
    select_all: Označit vše ({count})
    select_all_on_page: Označit vše na stránce ({count})
    deselect: Odznačit vše
    cancel: Zrušit
</i18n>

<template>
  <v-checkbox-btn
    id="activator-select-all-dialog"
    :indeterminate="someSelected"
    :model-value="allSelected"
    color="primary"
    @click="checkboxClicked"
  ></v-checkbox-btn>
  <v-dialog
    v-model="showDialog"
    v-if="canShowDialog"
    activator="#activator-select-all-dialog"
    location="bottom"
    max-width="800px"
  >
    <v-card>
      <v-card-title>
        {{ $t("title") }}
      </v-card-title>
      <v-card-text v-if="allSelected">
        {{ $tc("texts.all_selected", { count: selectedCount }) }}
      </v-card-text>
      <v-card-text v-else-if="allOnPageSelected">
        {{ $tc("texts.all_on_page_selected", { count: selectedCount }) }}
      </v-card-text>
      <v-card-text v-else-if="someSelected">
        {{ $t("texts.some_selected", { count: selectedCount }) }}
      </v-card-text>
      <v-card-text v-else-if="selectedCount == 0">
        {{ $t("texts.none_selected") }}
      </v-card-text>
      <v-card-actions>
        <v-btn color="primary" :disabled="allSelected" @click="selectAll">
          {{ $t("actions.select_all", { count: totalCount }) }}
        </v-btn>
        <v-btn
          color="primary"
          :disabled="allOnPageSelected"
          @click="selectAllOnPage"
        >
          {{ $t("actions.select_all_on_page", { count: onPageCount }) }}
        </v-btn>
        <v-btn color="primary" :disabled="!selectedCount" @click="deselect">
          {{ $t("actions.deselect") }}
        </v-btn>
        <v-btn color="primary" @click="showDialog = false">
          {{ $t("actions.cancel") }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
export default {
  name: "SelectAllCheckBox",

  emits: ["select-all", "select-all-on-page", "deselect"],

  props: {
    selectedCount: { type: Number },
    selectedOnPageCount: { type: Number },
    onPageCount: { type: Number },
    totalCount: { type: Number },
  },
  data() {
    return {
      showDialog: false,
      loading: false,
    };
  },
  computed: {
    allSelected() {
      return this.selectedCount == this.totalCount && !!this.totalCount;
    },
    someSelected() {
      return this.selectedCount > 0 && this.totalCount != this.selectedCount;
    },
    allOnPageSelected() {
      return (
        this.selectedCount == this.selectedOnPageCount &&
        this.selectedOnPageCount == this.onPageCount
      );
    },
    canShowDialog() {
      return this.showDialog && this.totalCount > 0;
    },
  },
  methods: {
    checkboxClicked(event) {
      event.preventDefault();
      this.showDialog = true;
    },
    deselect() {
      this.$emit("deselect");
      this.showDialog = false;
    },
    selectAllOnPage() {
      this.$emit("select-all-on-page");
      this.showDialog = false;
    },
    selectAll() {
      this.$emit("select-all");
      this.showDialog = false;
    },
  },
};
</script>
