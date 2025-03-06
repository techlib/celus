<!-- presents a bar with parts of different colors representing individual parts of a whole -->

<template>
  <div class="d-flex" :style="{ lineHeight: height + 'px' }">
    <v-tooltip location="bottom" v-for="(chunk, index) in data" :key="index">
      <template #activator="{ props }">
        <div
          v-bind="props"
          :style="{
            width: (100 * chunk.value) / total + '%',
            backgroundColor: chunk.color,
            textOverflow: 'ellipsis',
            overflow: 'hidden',
            whiteSpace: 'nowrap',
            height: height,
            transition: 'width .2s',
          }"
          class="text-center"
        >
          <span class="px-4" :class="textClass">{{ chunk.title }}</span>
        </div>
      </template>
      {{ showAllTooltipsAsOne ? overallTooltip : chunk.tooltip || chunk.title }}
    </v-tooltip>
  </div>
</template>

<script>
export default {
  name: "CompositionBar",

  props: {
    height: {
      type: String,
      default: "24",
    },
    data: {
      type: Array,
      required: true,
    },
    textClass: {
      type: String,
      default: "",
    },
    showAllTooltipsAsOne: {
      type: Boolean,
      default: false,
    },
  },

  computed: {
    total() {
      return this.data.reduce((acc, cur) => acc + cur.value, 0);
    },
    overallTooltip() {
      return this.data.map((chunk) => chunk.tooltip || chunk.title).join("; ");
    },
  },
};
</script>

<style scoped></style>
