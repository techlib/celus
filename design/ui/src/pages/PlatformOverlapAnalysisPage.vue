<i18n lang="yaml">
en:
  multiplatform_titles: Platform overlap
  relative: Display relative overlap
  info:
    The following table shows how many titles are shared between platforms. It contains only platforms which
    have at least one title common with other platform.
  info2:
    You can switch between absolute and relative overlap representation. If unclear, use the tooltip for each value
    in the table for explanation of the meaning of the number.

cs:
  multiplatform_titles: Překryv platforem
  relative: Zobrazit relativní překryv
  info:
    Následující tabulka ukazuje počet titulů sdílených mezi platformami. Obsahuje pouze platformy, které mají alespoň
    jeden titul společný s jinou platformou.
  info2:
    Můžete přepínat mezi absolutním a relativním vyjádřením překryvu. V případě nejasností můžete využít nápovědu
    pro každou buňku v tabulce, která obsahuje vysvětlení daného čísla.
</i18n>

<template>
  <v-container v-if="selectedOrganizationId" fluid>
    <v-row>
      <v-col>
        <h3 class="pt-3">{{ $t("multiplatform_titles") }}</h3>
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="12" lg="10" xl="7" v-text="$t('info')"></v-col>
      <v-col cols="12" lg="10" xl="7" class="pb-0">
        <v-alert type="info" colored-border border="left" elevation="4">
          <div>
            {{ $t("info2") }}
          </div>
        </v-alert>
      </v-col>
    </v-row>
    <v-row>
      <v-col class="overflow-auto px-8 mx-4">
        <PlatformOverlapTable />
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { mapActions, mapGetters, mapState } from "vuex";
import TitleList from "@/components/TitleList";
import InterestGroupSelector from "@/components/InterestGroupSelector";
import PlatformOverlapTable from "@/components/PlatformOverlapTable";

export default {
  name: "PlatformOverlapAnalysisPage",
  components: {
    PlatformOverlapTable,
  },

  computed: {
    ...mapState({
      selectedOrganizationId: "selectedOrganizationId",
    }),
  },
};
</script>
