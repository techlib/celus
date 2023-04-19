<!-- presents a bar with parts of different colors representing individual parts of a whole -->
<template>
  <div class="d-flex" :style="{ lineHeight: height + 'px' }">
    <v-tooltip bottom v-for="(chunk, index) in data" :key="index">
      <template #activator="{ on }">
        <div
          v-on="on"
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
          <span class="px-4" :class="textClass">{{ chunk.text }}</span>
        </div>
      </template>
      {{ chunk.tooltip || chunk.text }}
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
  },

  computed: {
    total() {
      return this.data.reduce((acc, cur) => acc + cur.value, 0);
    },
  },
};
</script>

<style scoped></style>
