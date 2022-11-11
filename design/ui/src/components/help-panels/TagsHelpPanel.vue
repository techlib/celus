<i18n lang="yaml">
en:
  p1: >
    Tags are used throughout Celus to group items of the same type together.
    They can be assigned to titles, organizations and platforms. Once assigned
    they may be used for filtering in the reporting section as well as in
    other parts of the application.
  p2: >
    Before tags can be used they must be created. Each tag has a class assigned
    which allows grouping similar tags together. For example, tags used to group
    titles from different collections can be grouped together under the class
    "Collection".
  link: For more information on tags, see the {target} section of the Celus documentation.
  target: Tags

cs:
  p1: >
    Štítky se používají v Celusu k seskupení položek stejného typu.
    Mohou být přiřazeny titulům, organizacím a platformám. Jakmile jsou přiřazeny,
    mohou být použity pro filtrování v sekci reporting, stejně jako v jiných
    částech aplikace.
  p2: >
    Předtím, než mohou být štítky použity, musí být vytvořeny. Každý štítek má
    přiřazený typ, který umožňuje seskupení podobných štítků. Například
    štítky použité k seskupení titulů z různých kolekcí mohou být seskupeny
    pod typem "Kolekce".
  link: Pro více informací o štítcích, podívejte se do sekce {target} Celus dokumentace.
  target: Tags
</i18n>

<template>
  <div>
    <p>{{ $t("p1") }}</p>
    <p>{{ $t("p2") }}</p>
    <p>
      <i18n path="link" tag="span">
        <template #target>
          <a
            href="https://docs.celus.net/tags.html"
            target="_blank"
            class="font-weight-black"
            >{{ $t("target") }}
            <v-icon small>fa fa-external-link-alt</v-icon>
          </a>
        </template>
      </i18n>
    </p>
  </div>
</template>

<script>
export default {
  name: "TagsHelpPanel",
};
</script>

<style scoped></style>
