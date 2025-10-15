<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml">
en:
  sushi_troubleshooting: SUSHI Troubleshooting
  ip_authentication: IP address based authentication
  ip_authentication_description: |
    Some SUSHI services rely on IP address based authentication in addition to
    the normal SUSHI credentials. Unfortunately, this is something which is hard
    to reliably detect from the client side and some platform providers do not
    inform about this.
  ip_authentication_description_2: |
    If you find that some of your SUSHI credentials are not working in CELUS, it might
    be necessary to register the IP addresses of this CELUS server with your provider. These are:
  ip_authentication_description_3: |
    Feel free to contact us at <a href="mailto:ask{'@'}celus.net">ask{'@'}celus.net</a>
    if you are not sure how to proceed.
  platform_table:
    name: Platform name
    short_name: Platform short name
    whitelisted_ir: IR whitelisted
  whitelisted_ir_platforms: Platforms with whitelisted IR reports
  whitelisted_ir_platforms_detail_1: Unfortunately some platforms are producing IR reports which are not correct or are inconsistent with the corresponding TR reports. In order to keep data clean in CELUS, we only allow harvesting of IR reports for platforms that we have thoroughly checked. See <a href="https://support.celus.net/support/solutions/articles/103000367118">this article</a> for more information.
  whitelisted_ir_platforms_detail_2: Here is a list of platforms currently whitelisted for IR harvesting.

cs:
  sushi_troubleshooting: Řešení problémů se SUSHI
  ip_authentication: Autentizace pomocí IP adresy
  ip_authentication_description: |
    Některé SUSHI služby vyžadují kromě normálních přihlašovacích údajů
    také autentizaci pomocí IP adresy. Bohužel, toto je něco, co je obtížné
    detekovat ze strany klienta a někteří poskytovatelé o tom neinformují.
  ip_authentication_description_2: |
    Pokud zjistíte, že některé z vašich přihlašovacích údajů pro SUSHI v CELUSu nefungují,
    bude možná nutné zaregistrovat IP adresy tohoto serveru u vašeho poskytovatele. Adresy jsou:
  ip_authentication_description_3: |
    Pokud nevíte, jak postupovat, neváhejte nás kontaktovat na
    <a href="mailto:ask{'@'}celus.net">ask{'@'}celus.net</a>.
  platform_table:
    name: Jméno platformy
    short_name: Krátké jméno platformy
    whitelisted_ir: prověřené IR
  whitelisted_ir_platforms: Platformy s prověřeným IR reportem
  whitelisted_ir_platforms_detail_1: Bohužel některé platformy poskytují IR reporty, které nejsou správné nebo jsou nekonzistentní s odpovídajícími TR reporty. Kvůli zajištění integrity dat ve CELUSu, je dovolené pouze stahovat IR reporty pro platformy, které jsme zevrubně zkontrolovali. Pro více informací viz <a href=" https://support.celus.net/support/solutions/articles/103000367118">tento článek</a>.
  whitelisted_ir_platforms_detail_2: Zde je seznam platforem, pro které jsme zkontrolovali stahování IR reportů.
</i18n>

<template>
  <div class="pa-3">
    <h2>{{ $t("sushi_troubleshooting") }}</h2>
    <section class="py-6">
      <h3 class="mb-4">{{ $t("ip_authentication") }}</h3>
      <p>{{ $t("ip_authentication_description") }}</p>
      <p>{{ $t("ip_authentication_description_2") }}</p>
      <HarvesterIPAddressList></HarvesterIPAddressList>
      <p class="mt-4" v-html="$t('ip_authentication_description_3')"></p>
    </section>
    <section class="py-6">
      <h3 class="mb-4">{{ $t("whitelisted_ir_platforms") }}</h3>
      <p v-html="$t('whitelisted_ir_platforms_detail_1')"></p>
      <p>{{ $t("whitelisted_ir_platforms_detail_2") }}</p>
      <v-data-table
        :loading="loadingPlatforms"
        :headers="headers"
        :items="platforms"
        :search="search"
        :items-per-page="itemsPerPage"
        v-model:sort-by="orderBy"
      >
        <template #top>
          <v-row>
            <v-spacer></v-spacer>
            <v-col cols="12" md="6" lg="4" class="px-3">
              <v-text-field
                v-model="search"
                :label="$t('labels.search')"
                append-inner-icon="fa fa-search"
                clearable
                clear-icon="fas fa-times"
              ></v-text-field>
            </v-col>
          </v-row>
        </template>
        <template #item.knowledgebase="{ item }">
          <CheckMark :model-value="true" />
        </template>
      </v-data-table>
    </section>
  </div>
</template>

<script>
import HarvesterIPAddressList from "@/components/sushi/HarvesterIPAddressList";
import cancellation from "@/mixins/cancellation";
import CheckMark from "@/components/util/CheckMark";

export default {
  name: "SushiTroubleshootingPage",

  mixins: [cancellation],

  components: { HarvesterIPAddressList, CheckMark },

  data() {
    return {
      platforms: [],
      loadingPlatforms: false,
      itemsPerPage: 25,
      search: "",
      orderBy: [{ key: "name", order: "asc" }],
    };
  },

  computed: {
    headers() {
      return [
        {
          title: this.$t("platform_table.name"),
          value: "name",
          key: "name",
        },
        {
          title: this.$t("platform_table.short_name"),
          value: "short_name",
          key: "short_name",
        },
        {
          title: this.$t("platform_table.whitelisted_ir"),
          value: "knowledgebase",
          key: "knowledgebase",
          sortable: false,
        },
      ];
    },
  },

  methods: {
    async loadPlatforms() {
      this.loadingPlatforms = true;
      const reply = await this.http({
        method: "GET",
        url: "/api/organization/-1/all-platform/?whitelisted_ir=true",
      });
      this.loadingPlatforms = false;
      if (!reply.error) {
        this.platforms = reply.response.data;
      }
    },
  },

  mounted() {
    this.loadPlatforms();
  },
};
</script>

<style scoped>
p {
  margin-bottom: 16px;
}
</style>
