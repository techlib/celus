<i18n lang="yaml" src="../locales/common.yaml"></i18n>
<i18n lang="yaml" src="../locales/dialog.yaml"></i18n>

<i18n lang="yaml">
en:
  harvests_view: Harvest Overview
  harvest_intro: |
    <p>'Harvests' group together related data downloads. They are either created automatically
    by Celus when it downloads new data, or are created by the user when he manually requests
    harvesting of data for selected credentials.</p>
    <p>You can use the table below to get an overview of currently running harvests as well
    as past ones. By clicking on the <span class="fa fa-external-link-alt"></span> symbol,
    you can see the individual downloads comprising each harvest and their status.</p>

cs:
  harvests_view: Přehled sklizní
  harvest_intro: |
    <p>'Sklizně' sdružují dohromady příbuzná stahování. Celus je buď vytváří automaticky, když
      stahuje nová data, nebo jsou vytvořeny uživatelem ve chvíli, kdy zadá požadavek na stažení
      dat pro vybrané přihlašovací údaje.</p>
    <p>Následující tabulka poskytuje přehled aktuálně probíhajících sklizní i těch, které již
      skončily. Kliknutím na symbol <span class="fa fa-external-link-alt"></span> získáte
      detaily jednotlivých stahování pro každou sklizeň včetně jejich stavu.</p>
</i18n>

<template>
  <v-container fluid>
    <v-row>
      <v-col>
        <h2 v-text="$t('harvests_view')"></h2>
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <v-card elevation="4">
          <v-container fluid>
            <v-row>
              <v-col class="mx-3" v-html="$t('harvest_intro')"> </v-col>
            </v-row>
            <v-row>
              <v-col class="overflow-auto">
                <HarvestsTable
                  :show-organization="showManagementStuff"
                  show-platform
                />
              </v-col>
            </v-row>
          </v-container>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { mapGetters, mapState } from "vuex";
import HarvestsTable from "@/components/HarvestsTable";

export default {
  name: "SushiFetchAttemptsPage",
  components: {
    HarvestsTable,
  },
  data() {
    return {};
  },
  computed: {
    ...mapState({
      user: "user",
    }),
    ...mapGetters({
      showManagementStuff: "showManagementStuff",
    }),
  },
};
</script>

<style scoped lang="scss"></style>
