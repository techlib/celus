<i18n src="@/locales/common.yaml" lang="yaml"></i18n>
<i18n lang="yaml">
en:
  header: Supported non-SUSHI platforms
  desc0: |
    There are many non-COUNTER-compliant platforms. They usually provide their statistics in
    a custom format specific to the platform or COUNTER format not harvestable via SUSHI.
  desc1: |
    For the following platforms, CELUS supports the <strong>import of raw data files</strong>.
    This means you can upload the raw data files from your platform, and CELUS will
    automatically parse and import the data.
  desc2: |
    We are constantly working on adding more platforms to this list.
    If you need CELUS to process a report not listed
    <a href="https://support.celus.net/support/solutions/articles/103000096445-non-counter-platforms-processing-in-celus">here</a>
    and which does not support COUNTER, please <strong>let us know</strong>
    at <a href="mailto:ask@celus.net">ask@celus.net</a>.

cs:
  header: Podporované non-SUSHI platformy
  desc0: |
    Existuje mnoho platform, které ne zcela vyhovují COUNTER standardům.
    Obvykle poskytují své statistiky ve vlastním formátu specifickém pro danou platformu
    nebo v COUNTER formátu, který se ovšem nedá stáhnout přes SUSHI.
  desc1: |
    Pro následující platformy podporuje CELUS <strong>import dat z neupravených datových souborů</strong>.
    To znamená, že můžete nahrát datové soubory z vaší
    platformy, tak jak jste je obdrželi, a CELUS je automaticky zpracuje a naimportuje.
  desc2: |
    Stále připravujeme podporu pro nové platformy a níže zobrazený seznam rozšiřujeme.
    Pokud potřebujete, aby CELUS zpracoval report, který není na
    <a href="https://support.celus.net/support/solutions/articles/103000096445-non-counter-platforms-processing-in-celus">seznamu</a>,
    <strong>dejte nám vědět</strong> na <a href="mailto:ask@celus.net">ask@celus.net</a>.
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
