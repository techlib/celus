<i18n lang="yaml">
en:
  platform_overlap: Platform overlap
  platform_vs_platform_overlap: Overlap with individual platforms
  platform_vs_all_overlap: Overlap with all other platforms
  overlap_pyramid: Portfolio optimization
  cancel_simulation: Cancellation simulation
  warning:
    The following tabs offer different views of data related to titles available on more than one platform.
    Please keep in mind that Celus only has usage data to work with and does not know the particulars of your
    subscriptions. Therefore the data below are meant as just pointers and you should <strong>always investigate deeper
    before taking any action</strong> based on it.
  info:
    The following table shows how many titles are shared between platforms. It contains only platforms which
    have at least one title common with other platform.
  info2: You can switch between absolute and relative overlap representation.
  info2_tooltips: If unclear, use the tooltip for each value in the table for explanation of the meaning of the number.
  info2_no_tooltips: Please note that tooltips were disabled for performance reasons due to the large number of platforms.
  info_vs_all:
    The following table shows for each platform how many titles are shared with other platforms. The right part of
    the table shows interest in the overlapping titles.
  info_vs_all2: You can use tooltips for each value in the table for explanation of the meaning of the number.
  info_pyramid:
    "<p>This view simulates creation of a portfolio from the currently available platforms. It starts with an empty
    table and adds the platform which contains titles with the highest sum of interest into the first row. A second
    platform is then selected, which adds new titles (titles not available from the first platform) with the highest
    sum of interest. This process is repeated until all the platforms are added to the table.
    </p>
    <p>
    The result is a list of platforms sorted by how much new and interesting content they bring to the porfolio.
    </p>
    <p>
    If you wanted to select only subset of your current portfolio and ensure that you cover the most interest possible,
    you would simply select the appropriate level of interest you wanted to keep in the <em>Cumulative interest</em> column and
    keep all the platforms above this cut-off value.
    </p>
    <p><strong>Note</strong>: You can limit the displayed data to only specific title types in order to
    distinguish between database, journal and book interest.
    </p>"
  info_cancel:
    "<p>This view shows an interactive table where you can simulate real-time impact of cancelling subscription to one
    or more platforms by simply deselecting it. The table is <em>live</em> and recalculates data after each platform is deselected
    to correctly account for titles available from more than one platform.</p>
    <p>
    <p><strong>Note</strong>: The interest show in this table is always the total interest in titles available from a specific platform,
    not only interest realized through that platform. That means that if you had access to 'Nature' from platforms A and B
    with 100 and 400 article downloads respectively, both platforms would show interest
    of 500. On the other side, it would be calculated as 'unique interest' only if the other platform was deselected.
    </p>
    "

cs:
  platform_overlap: Překryv platforem
  platform_vs_platform_overlap: Překryv s jednotlivými platformami
  platform_vs_all_overlap: Překryv se všemi ostatními platformami
  overlap_pyramid: Optimalizace portofia
  cancel_simulation: Simulace zrušení
  warning:
    Následující záložky poskytují různý pohled na data o titulech dostupných na více platformách.
    Při jejich interpretaci mějte prosím vždy na vědomí, že Celus má k dispozici pouze data o využívání elektronických
    zdrojů a neví nic o detailech vašeho předplatného k jednotlivým titulům. Následující informace by měly být brány
    jen jako ukazatele na potenciálně zajímavé skutečnosti. Vždy <strong>proveďte detailnější analýzu dat, než
    se rozhodnete na základě těchto dat dělat nějaké změny</strong>.
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
  info_pyramid:
    "<p>Tento pohled simuluje vytvoření portfolia ze současně dostupných platforem. Začíná prázdnou tabulkou, do které
    přidá platformu s nejvyšším součtem zájmů v obsažených titulech. Jako druhá se přídá platforma, která má nejvyšší
    součet zájmu v nově přidaných titulech (titulech, které nejsou dostupné na první přidané platformě). Tento proces
    se pak opakuje dokud nejsou do tabulky přidané všechny platformy.
    </p>
    <p>
    Výsledkem je seznam platforem seřazený podle toho, jak moc nového a zajímavého obsahu přinášejí do portfolia.
    </p>
    <p>
    Pokud byste měli za úkol vybrat podmnožinu současného portfolia, která pokrývá maximum současného zájmu,
    stačilo by prostě určit jak velkou část zájmu chcete pokrýt ze sloupce <em>Kumulovaný zájem</em> a ponechat všechny
    platformy, které jsou nad tímto řádkem.
    </p>
    <p><strong>Poznámka</strong>: Můžete omezit zobrazená data je na specifické typy titulů a odlišit tak zájem o databáze,
    časopisy nebo knihy.
    </p>"
  info_cancel:
    "<p>Tento pohled obsahuje interaktivní tabulku, která umožňuje simulovat dopad zrušení předplatného k jedné nebo více
    platformám. Stačí odstranit zaškrtnutí platformy v tabulce a tabulka interaktivně přepočítá data pro ostatní platformy
    i s ohledem na překryv titulů na více platformách.
    </p>
    <p><strong>Poznámka</strong>: Zájem zobrazený v tabulce je vždy celkový zájem o tituly, které jsou dostupné na dané platformě,
    nikoli jen zájem realizovaný přes danou platformu. Pokud bychom tedy měli například přístup k časopisu 'Nature'
    na platformách A a B se 100 a 400 staženými články, obě platformy by ukazovaly hodnotu zájmu 500. Na druhou stranu
    tento zájem by se objevil jako 'unikátní zájem' pouze v případě, že by jedna z platforem nebyla zaškrtnutá.
    </p>
    "
</i18n>

<template>
  <v-container v-if="selectedOrganizationId" fluid>
    <v-row>
      <v-col xl="8">
        <v-alert type="warning" outlined
          ><span v-html="$t('warning')"></span
        ></v-alert>
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <v-card elevation="4">
          <v-tabs
            v-model="tab"
            dark
            background-color="info"
            centered
            slider-color="#ffffff33"
            slider-size="48"
          >
            <v-tab href="#one-vs-all" v-text="$t('platform_vs_all_overlap')">
            </v-tab>
            <v-tab
              href="#one-vs-one"
              v-text="$t('platform_vs_platform_overlap')"
            >
            </v-tab>
            <v-tab href="#pyramid" v-text="$t('overlap_pyramid')"> </v-tab>
            <v-tab href="#cancel" v-text="$t('cancel_simulation')"> </v-tab>

            <v-tab-item value="one-vs-all">
              <v-container class="px-8 pb-10">
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
              <v-container class="px-8 pb-10">
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
                        <span>
                          {{
                            disableTooltips2
                              ? $t("info2_no_tooltips")
                              : $t("info2_tooltips")
                          }}
                        </span>
                      </div>
                    </v-alert>
                  </v-col>
                </v-row>
                <v-row>
                  <v-col>
                    <PlatformOverlapTable
                      @disableTooltips="disableTooltips2m"
                    />
                  </v-col>
                </v-row>
              </v-container>
            </v-tab-item>

            <v-tab-item value="pyramid">
              <v-container class="px-8 pb-10">
                <v-row>
                  <v-col
                    cols="12"
                    lg="12"
                    xl="8"
                    v-html="$t('info_pyramid')"
                  ></v-col>
                </v-row>
                <v-row>
                  <v-col xl="8">
                    <OverlapPyramidWidget />
                  </v-col>
                </v-row>
              </v-container>
            </v-tab-item>

            <v-tab-item value="cancel">
              <v-container class="px-8 pb-10">
                <v-row>
                  <v-col
                    cols="12"
                    lg="12"
                    xl="8"
                    v-html="$t('info_cancel')"
                  ></v-col>
                </v-row>
                <v-row>
                  <v-col xl="8">
                    <CancelSimulationWidget />
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
import { mapState } from "vuex";
import PlatformOverlapTable from "@/components/PlatformOverlapTable";
import PlatformVsAllOverlapTable from "@/components/PlatformVsAllOverlapTable";
import OverlapPyramidWidget from "@/components/OverlapPyramidWidget";
import CancelSimulationWidget from "@/components/CancelSimulationWidget";

export default {
  name: "PlatformOverlapAnalysisPage",
  components: {
    CancelSimulationWidget,
    OverlapPyramidWidget,
    PlatformOverlapTable,
    PlatformVsAllOverlapTable,
  },

  data() {
    return {
      tab: "one-vs-all",
      disableTooltips2: false,
    };
  },

  computed: {
    ...mapState({
      selectedOrganizationId: "selectedOrganizationId",
    }),
  },

  methods: {
    disableTooltips2m(value) {
      this.disableTooltips2 = value;
    },
  },
};
</script>
