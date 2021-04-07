<template>
  <div class="d-flex flex-column full-width">
    <div class="label">{{ label }}</div>
    <v-container class="ma-0 pa-0" fluid>
      <v-row no-gutters>
        <v-col class="pane">
          <!--div class="pane-title">Available</div-->
          <slot></slot>
          <div class="pane-internal">
            <v-list dense v-if="selectable.length">
              <template v-for="item in selectable">
                <v-list-item
                  :key="item[itemValue]"
                  @click="selectItem(item)"
                  class="pr-1"
                >
                  <v-list-item-content>{{
                    item[itemText]
                  }}</v-list-item-content>
                  <v-list-item-icon>
                    <v-icon small>fa fa-angle-right</v-icon>
                  </v-list-item-icon>
                </v-list-item>
                <!--v-divider :key="'div' + item[itemValue]" /-->
              </template>
            </v-list>
            <div v-else class="mx-4 my-2">{{ emptyHint }}</div>
          </div>
        </v-col>
        <v-col class="pane">
          <div class="d-flex justify-space-between">
            <div class="pane-title">Selected</div>
            <div class="pr-1 pt-1" v-if="selected.size">
              <v-icon @click="clearAll()">fa fa-times-circle</v-icon>
            </div>
          </div>
          <div class="pane-internal">
            <v-list dense>
              <template v-for="item in selectedItems">
                <v-list-item
                  :key="item[itemValue]"
                  @click="deselectItem(item)"
                  class="pr-1"
                >
                  <v-list-item-content>{{
                    item[itemText]
                  }}</v-list-item-content>
                  <v-list-item-icon>
                    <v-icon small>fa fa-times</v-icon>
                  </v-list-item-icon>
                </v-list-item>
                <!--v-divider :key="'div' + item[itemValue]" /-->
              </template>
            </v-list>
          </div>
        </v-col>
      </v-row>
    </v-container>
  </div>
</template>

<script>
export default {
  name: "TwoPaneSelector",

  props: {
    value: { required: true, type: Array },
    items: { required: true, type: Array },
    itemText: { default: "text", type: String },
    itemValue: { default: "value", type: String },
    emptyHint: { default: "", type: String },
    label: { default: "", type: String },
  },

  data() {
    let extra = new Map();
    let selected = new Set([...this.value]);
    this.items
      .filter((item) => selected.has(item[this.itemValue]))
      .forEach((item) => extra.set(item[this.itemValue], item));
    console.debug("init", selected, extra, this.items);

    return {
      selected: selected,
      extraItems: extra, // stores data for selected items which might be removed from items by upstream
    };
  },

  computed: {
    selectable() {
      return this.items.filter(
        (item) => !this.selected.has(item[this.itemValue])
      );
    },
    selectedItems() {
      return this.allItems.filter((item) =>
        this.selected.has(item[this.itemValue])
      );
    },
    allItems() {
      let itemValues = new Set(this.extraItems.keys());
      return [
        ...this.extraItems.values(),
        ...this.items.filter((item) => !itemValues.has(item[this.itemValue])),
      ];
    },
  },

  methods: {
    selectItem(item) {
      this.selected.add(item[this.itemValue]);
      this.extraItems.set(item[this.itemValue], item);
      // TODO: remove the following reactivity hack when upgrading to Vue 3
      this.selected = new Set([...this.selected]);
    },
    deselectItem(item) {
      this.selected.delete(item[this.itemValue]);
      // TODO: remove the following reactivity hack when upgrading to Vue 3
      this.selected = new Set([...this.selected]);
    },
    clearAll() {
      this.selected = new Set();
      this.extraItems = new Map();
    },
    async revalidateSelected(validator) {
      // this is used to filter the selected values that come from extraItems
      // if calls validator with a list of itemValues and expects an iterable with filtered
      // itemValues as a result. Validator should be async
      let toValidate = [];
      this.extraItems.forEach((value, key) => {
        if (this.selected.has(key)) {
          toValidate.push(key);
        }
      });
      console.debug("revalidating", toValidate);
      let validated = await validator(toValidate);
      let newSelected = new Set();
      let allowed = new Set(validated);
      this.selected.forEach((value) => {
        if (allowed.has(value)) {
          newSelected.add(value);
        }
      });
      this.selected = newSelected;
      console.debug("revalidated", newSelected);
    },
  },

  watch: {
    selected() {
      this.$emit(
        "input",
        this.selectedItems.map((item) => item[this.itemValue])
      );
    },
  },
};
</script>

<style scoped lang="scss">
div.pane {
  border: solid 2px #dddddd;
  min-width: 10rem;
  min-height: 5rem;
  max-height: 25rem;

  .pane-internal {
    max-height: 20rem;
    overflow: auto;
  }

  &:first-child {
    //margin-right: 2px;
    border-right: none;
  }

  div.pane-title {
    margin-left: 0.5rem;
    font-size: 75%;
    font-weight: 400;
  }
}

div.label {
  font-size: 87.5%;
}

.full-width {
  width: 100%;
}
</style>
