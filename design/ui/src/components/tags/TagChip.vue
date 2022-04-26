<template>
  <v-tooltip bottom v-if="tag.desc">
    <template #activator="{ on }">
      <v-chip
        :small="small"
        :key="tag.pk"
        :color="color"
        :text-color="tag.text_color"
        :outlined="outlined"
        class="pt-0"
        :close="removable"
        @click:close="close"
        v-on="on"
      >
        <v-icon x-small class="pr-2" v-if="!hideIcon && !showClass"
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
    {{ tag.desc }}
  </v-tooltip>

  <v-chip
    v-else
    :small="small"
    :key="tag.pk"
    :color="color"
    :text-color="tag.text_color"
    :outlined="outlined"
    class="pt-0"
    :close="removable"
    @click:close="close"
  >
    <v-icon x-small class="pr-2" v-if="!hideIcon && !showClass"
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
  name: "TagChip",

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
      const bgc = color(this.tag.text_color);
      const txc = color(this.tag.bg_color);
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
      }
      return this.tag.bg_color;
    },
  },

  methods: {
    close() {
      this.$emit("remove", this.tag.pk);
    },
  },
};
</script>

<style lang="scss" scoped>
.chip-class {
  border-radius: 14px 0 0 14px;
  font-size: 80%;
  opacity: 90%;
  margin: 0 8px 0 -10px;
  line-height: 28px;
  padding: 0 4px;

  &.small {
    line-height: 20px;
  }
}
</style>
