<i18n lang="yaml">
en:
  tour_text_app-bar: |
    Welcome to Celus. <br>
    It seems this is the first time you are using it. Please let us quickly show you the basic
    parts of the user interface.
  tour_text_side-panel: |
    The side-panel contains the main navigation of the application. All functions related
    to your data can be found there.
  tour_text_organization-select: |
    Use this drop-down menu to select the organization for which you want to see the data.<br>
    This is a global option which influences almost everything you see in the rest of the application
  tour_text_date-range: |
    Click this control to select a different range of dates that should be displayed.<br>
    The selected range is applied globally to most data displayed in Celus.
  tour_text_user-avatar: |
    Click the avatar to get to the user page. It will show you some basic info and settings
    of your account
  tour_text_menu-show-button: |
    You can use this button to hide/show the side panel. It is especially useful on smaller
    displays.

cs:
  tour_text_app-bar: |
    Vítejte v aplikaci Celus. <br>
    Zdá se, že jste tu poprvé. Rádi bychom Vám v rychlosti ukázali základní prvky uživatelského rozhraní.
  tour_text_side-panel: |
    Postranní panel obsahuje hlavní navigaci celé aplikace. Všechny funkce týkající se Vašich dat najdete zde.
  tour_text_organization-select: |
    Tento výběr můžete použít pro výběr organizace, pro kterou chcete zobrazit data.<br>
    Je to globální nastavení, které ovlivňuje téměř všechna data, která se v aplikaci zobrazí.
  tour_text_date-range: |
    Kliknutím na tento prvek můžete měnit období, za které se budou zobrazovat data.<br>
    Vybraný rozsah se používá globálně pro většinu dat, kterou v aplikaci uvidíte.
  tour_text_user-avatar: |
    Kliknutím na ikonku avatara přejdete na uživatelskou stránku. Tam najdete základní informace a
    nastavení svého účtu.
  tour_text_menu-show-button: |
    Toto tlačítko můžete použít pro skrytí a zobrazení postranního panelu. To se hodí především na menších
    obrazovkách.
</i18n>

<template>
  <v-tour
    :name="name"
    :steps="tourSteps"
    :options="{ highlight: true, debug: false }"
    :callbacks="{ onFinish: onTourFinished, onSkip: onSkipTour }"
  ></v-tour>
</template>
<script>
import { mapActions, mapGetters } from "vuex";

export default {
  name: "UITour",
  props: {
    name: { required: true },
  },

  data() {
    return {
      allSteps: {
        basic: [
          {
            element: "app-bar",
            placement: "bottom",
            _filter: (context) => context.tourNeverSeen,
          },
          {
            element: "side-panel",
            placement: "right",
          },
          {
            element: "organization-select",
            placement: "bottom-start",
            _filter: (context) => context.consortialInstall,
          },
          {
            element: "date-range",
            placement: "bottom",
          },
          {
            element: "user-avatar",
            placement: "left-start",
          },
          {
            element: "menu-show-button",
            placement: "left-start",
          },
        ],
      },
    };
  },

  computed: {
    ...mapGetters({
      tourFinished: "tourFinished",
      consortialInstall: "consortialInstall",
      tourNeverSeen: "tourNeverSeen",
    }),
    tourSteps() {
      let context = {
        consortialInstall: this.consortialInstall,
        tourNeverSeen: this.tourNeverSeen(this.name),
      };
      return this.allSteps[this.name]
        .filter((item) => ("_filter" in item ? item._filter(context) : true))
        .map((item) => {
          return {
            target: `[data-tour="${item.element}"]`,
            content: this.$t(`tour_text_${item.element}`),
            params: {
              placement: item.placement || "auto",
            },
          };
        });
    },
  },

  methods: {
    ...mapActions({
      backstageChangeTourStatus: "backstageChangeTourStatus",
    }),
    onTourFinished() {
      this.backstageChangeTourStatus({ tourName: this.name, status: true });
    },
    onSkipTour() {
      this.backstageChangeTourStatus({ tourName: this.name, status: true });
    },
  },
};
</script>
