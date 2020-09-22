<i18n lang="yaml">
en:
  title: Sorry, but this page does not exist
  note: Maybe one of the options from the menu could be helpful.

cs:
  title: Je nám to líto, ale tato stránka neexistuje
  note: Možná Vás zaujme některé z položek v nabídce menu.
</i18n>

<template>
  <section class="pa-5">
    <h1>{{ $t("title") }} <v-icon x-large>far fa-frown</v-icon></h1>
    <p class="pt-4">{{ $t("note") }}</p>
  </section>
</template>

<script>
export default {
  name: "NotFoundPage",
};
</script>

<style scoped></style>
