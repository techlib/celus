<i18n lang="yaml">
en:
  platform_overlap: Platform overlap
  platform_vs_platform_overlap: Overlap with individual platforms
  platform_vs_all_overlap: Overlap with all other platforms
  info:
    The following table shows how many titles are shared between platforms. It contains only platforms which
    have at least one title common with other platform.
  info2:
    You can switch between absolute and relative overlap representation. If unclear, use the tooltip for each value
    in the table for explanation of the meaning of the number.
  info_vs_all:
    The following table shows for each platform how many titles are shared with other platforms. The right part of
    the table shows interest in the overlapping titles.
  info_vs_all2: You can use tooltips for each value in the table for explanation of the meaning of the number.

cs:
  platform_overlap: Překryv platforem
  platform_vs_platform_overlap: Překryv s jednotlivými platformami
  platform_vs_all_overlap: Překryv se všemi ostatními platformami
  info:
    Následující tabulka ukazuje počet titulů sdílených mezi platformami. Obsahuje pouze platformy, které mají alespoň
    jeden titul společný s jinou platformou.
  info2:
    Můžete přepínat mezi absolutním a relativním vyjádřením překryvu. V případě nejasností můžete využít nápovědu
    pro každou buňku v tabulce, která obsahuje vysvětlení daného čísla.
  info_vs_all:
    Následující tabulka ukazuje, kolik titulů platforma sdílí s ostatními platformami. Pravá část tabulky pak ukazuje
    zájem o tituly, které se překrývají s ostaními platformami.
  info_vs_all2: Můžete použít tooltipy k jednotlivým buňkám pro vysvětlení jejich významu.
</i18n>

<template>
  <v-container v-if="selectedOrganizationId" fluid>
    <!--v-row>
      <v-col>
        <h3 class="pt-3 text-h5">{{ $t("platform_overlap") }}</h3>
      </v-col>
    </v-row-->
    <v-row>
      <v-col>
        <v-card elevation="4">
          <v-tabs
            v-model="tab"
            dark
            background-color="indigo"
            centered
            slider-color="pink"
          >
            <v-tab href="#one-vs-all" v-text="$t('platform_vs_all_overlap')">
            </v-tab>
            <v-tab
              href="#one-vs-one"
              v-text="$t('platform_vs_platform_overlap')"
            >
            </v-tab>

            <v-tab-item value="one-vs-all">
              <v-container class="mx-4 pb-10">
                <v-row>
                  <v-col
                    cols="12"
                    lg="10"
                    xl="7"
                    v-text="$t('info_vs_all')"
                  ></v-col>
                  <v-col cols="12" lg="10" xl="7" class="pb-0">
                    <v-alert
                      type="info"
                      colored-border
                      border="left"
                      elevation="4"
                    >
                      <div>
                        {{ $t("info_vs_all2") }}
                      </div>
                    </v-alert>
                  </v-col>
                </v-row>
                <v-row>
                  <v-col class="overflow-auto">
                    <PlatformVsAllOverlapTable />
                  </v-col>
                </v-row>
              </v-container>
            </v-tab-item>

            <v-tab-item value="one-vs-one">
              <v-container class="mx-4 pb-10">
                <v-row>
                  <v-col cols="12" lg="10" xl="7" v-text="$t('info')"></v-col>
                  <v-col cols="12" lg="10" xl="7" class="pb-0">
                    <v-alert
                      type="info"
                      colored-border
                      border="left"
                      elevation="4"
                    >
                      <div>
                        {{ $t("info2") }}
                      </div>
                    </v-alert>
                  </v-col>
                </v-row>
                <v-row>
                  <v-col>
                    <PlatformOverlapTable />
                  </v-col>
                </v-row>
              </v-container>
            </v-tab-item>
          </v-tabs>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { mapActions, mapGetters, mapState } from "vuex";
import PlatformOverlapTable from "@/components/PlatformOverlapTable";
import PlatformVsAllOverlapTable from "@/components/PlatformVsAllOverlapTable";

export default {
  name: "PlatformOverlapAnalysisPage",
  components: {
    PlatformOverlapTable,
    PlatformVsAllOverlapTable,
  },

  data() {
    return {
      tab: "one-vs-all",
    };
  },

  computed: {
    ...mapState({
      selectedOrganizationId: "selectedOrganizationId",
    }),
  },
};
</script>
