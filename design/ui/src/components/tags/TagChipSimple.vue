<template>
  <v-chip
    :size="small ? 'small' : 'default'"
    :key="tag.pk"
    :color="tag.bg_color"
    variant="flat"
    class="pt-0"
    :closable="removable"
    :to="to"
    @click:close="close"
  >
    <v-icon size="x-small" class="mr-2" v-if="!hideIcon && !showClass"
      >fa fa-tag</v-icon
    >
    <span
      v-if="showClass"
      :style="{
        backgroundColor: classBgColor,
        color: classTextColor,
      }"
      class="chip-class"
      :class="{ small: small }"
      >{{ tag.tag_class.name }}</span
    >
    {{ text }}
  </v-chip>
</template>

<script>
import color from "color";

export default {
  name: "TagChipSimple",

  props: {
    tag: { required: true, type: Object },
    showClass: {
      default: false,
      type: Boolean,
    },
    hideIcon: {
      default: false,
      type: Boolean,
    },
    small: {
      default: false,
      type: Boolean,
    },
    removable: {
      // if given an icon for removing the tag will be show and the component
      // will emit a "remove" event
      default: false,
      type: Boolean,
    },
    disabled: {
      default: false,
      type: Boolean,
    },
    link: {
      // should the chip be a clickable link pointing to filtered list of
      // tagged items
      default: false,
      type: Boolean,
    },
  },

  computed: {
    text() {
      return this.tag.name;
    },
    color() {
      if (this.tag.bg_color === "#FFFFFF") {
        return this.tag.text_color;
      }
      return this.tag.bg_color;
    },
    outlined() {
      return this.tag.bg_color === "#FFFFFF";
    },
    classBgColor() {
      // class colors are reversed from normal colors
      let bgc = null;
      let txc = null;
      bgc = color(this.tag.text_color);
      txc = color(this.tag.bg_color);
      if (
        txc.contrast(bgc) < 8 &&
        txc.contrast(bgc) < txc.contrast(color("#FFFFFF"))
      ) {
        return "#FFFFFF";
      }
      return this.tag.text_color;
    },
    classTextColor() {
      const bgc = color(this.classBgColor);
      const txc = color(this.tag.bg_color);
      if (
        txc.contrast(bgc) < 8 &&
        bgc.contrast(txc) < bgc.contrast(color("#FFFFFF"))
      ) {
        return "#FFFFFF";
      } else {
        return this.tag.bg_color;
      }
    },
    to() {
      if (this.link) {
        switch (this.tag.tag_class.scope) {
          case "title":
            return {
              name: "title-list",
              query: {
                tags: this.tag.pk,
              },
            };
          case "organization":
            return {
              name: "organization-list",
              query: {
                tags: this.tag.pk,
              },
            };
          case "platform":
            return {
              name: "platform-list",
              query: {
                tags: this.tag.pk,
              },
            };
        }
      }
      return null;
    },
  },

  methods: {
    close() {
      this.$emit("remove", {
        tagId: this.tag.pk,
      });
    },
  },
};
</script>

<style lang="scss" scoped>
.chip-class {
  border-radius: 14px 0 0 14px;
  font-size: 80%;
  opacity: 0.9;
  margin: 0 8px 0 -10px;
  line-height: 28px;
  padding: 0 4px;

  &.small {
    line-height: 20px;
    margin: 0 8px 0 -7px !important;
  }
}
</style>
