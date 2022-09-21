<i18n lang="yaml">
en:
  p1: >
    This is a help panel. It contains short context specific help for the page
    you are currently visiting. You can close it by clicking the close button.

cs:
  p1: >
    Toto je panel s nápovědou. Obsahuje krátkou nápovědu pro aktuální stránku.
    Panel můžete zavřít kliknutím na tlačítko zavřít.
</i18n>

<template>
  <p>{{ $t("p1") }}</p>
</template>

<script>
export default {
  name: "DashboardHelpPanel",
};
</script>

<style scoped></style>
