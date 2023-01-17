<i18n src="@/locales/common.yaml" lang="yaml"></i18n>
<i18n lang="yaml">
en:
  header: Supported non-COUNTER platforms
  desc0: |
    There are still many platforms which do not support COUNTER statistics. They usually provide
    their statistics in a custom format specific to the platform.
  desc1: |
    For the following platforms, Celus supports the <strong>import of raw non-COUNTER data</strong>
    files. This means that you can upload the raw data files from your
    platform and Celus will automatically parse the data and import it.
  desc2: |
    We are constantly working on adding more platforms to this list. If you have
    a platform that is <strong>not listed here</strong> and which does not support COUNTER, please <strong>let us know</strong> at
    <a href="mailto:ask@celus.net">ask@celus.net</a>.

cs:
  header: Podporované non-COUNTER platformy
  desc0: |
    Stále existuje mnoho platform, které nepodporují COUNTER statistiky. Obvykle poskytují své statistiky
    ve vlastním formátu specifickém pro danou platformu.
  desc1: |
    Pro následující platformy podporuje Celus import non-COUNTER dat z neupravených datových souborů.
    To znamená, že můžete nahrát datové soubory z vaší
    platformy, tak jak jste je obdrželi, a Celus je automaticky zpracuje a importuje.
  desc2: |
    Stále připravujeme podporu pro nové platformy a níže zobrazený seznam rozšiřujeme. Pokud máte
    platformu, která <strong>není v seznamu</strong> a která nepodporuje COUNTER, <strong>dejte nám vědět</strong> na
    <a href="mailto:ask@celus.net">ask@celus.net</a>.
</i18n>

<template>
  <v-container>
    <v-row>
      <v-col>
        <h2 class="pb-4">{{ $t("header") }}</h2>
      </v-col>
    </v-row>

    <v-row>
      <v-col>
        <p v-html="$t('desc0')"></p>
        <p v-html="$t('desc1')"></p>
        <p v-html="$t('desc2')"></p>
      </v-col>
    </v-row>

    <v-row>
      <v-col>
        <SupportedNonCounterPlatformsList />
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import SupportedNonCounterPlatformsList from "@/components/SupportedNonCounterPlatformsList";

export default {
  name: "SupportedNonCounterPlatformsPage",

  components: { SupportedNonCounterPlatformsList },
};
</script>

<style scoped></style>
