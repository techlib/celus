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
    If you find that some of your SUSHI credentials are not working in Celus, it might
    be necessary to register the IP addresses of this Celus server with your provider. These are:
  ip_authentication_description_3: |
    Feel free to contact us at <a href="mailto:ask@celus.net">ask@celus.net</a>
    if you are not sure how to proceed.
cs:
  sushi_troubleshooting: Řešení problémů se SUSHI
  ip_authentication: Autentizace pomocí IP adresy
  ip_authentication_description: |
    Některé SUSHI služby vyžadují kromě normálních přihlašovacích údajů
    také autentizaci pomocí IP adresy. Bohužel, toto je něco, co je obtížné
    detekovat ze strany klienta a někteří poskytovatelé o tom neinformují.
  ip_authentication_description_2: |
    Pokud zjistíte, že některé z vašich přihlašovacích údajů pro SUSHI v Celusu nefungují,
    bude možná nutné zaregistrovat IP adresy tohoto serveru u vašeho poskytovatele. Adresy jsou:
  ip_authentication_description_3: |
    Pokud nevíte, jak postupovat, neváhejte nás kontaktovat na
    <a href="mailto:ask@celus.net">ask@celus.net</a>.
</i18n>
<template>
  <div class="pa-3">
    <h2>{{ $t("sushi_troubleshooting") }}</h2>
    <section class="py-6">
      <h3 class="mb-4">{{ $t("ip_authentication") }}</h3>
      <p>{{ $t("ip_authentication_description") }}</p>
      <p>{{ $t("ip_authentication_description_2") }}</p>
      <HarvesterIPAddressList />
      <p class="mt-4" v-html="$t('ip_authentication_description_3')"></p>
    </section>
  </div>
</template>

<script>
import HarvesterIPAddressList from "@/components/sushi/HarvesterIPAddressList";

export default {
  name: "SushiTroubleshootingPage",

  components: { HarvesterIPAddressList },
};
</script>

<style scoped></style>
