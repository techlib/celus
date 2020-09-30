<template>
  <svg
    class="pie"
    xmlns="http://www.w3.org/2000/svg"
    :height="size"
    :width="size"
    viewBox="-1 -1 2 2"
  >
    <g transform="rotate(-90)">
      <path
        v-for="(path, index) in paths"
        :d="`M ${path.startX} ${path.startY} A 1 1 0 ${path.longArc} 1 ${path.endX} ${path.endY} L 0 0`"
        :key="index"
        :fill="path.color"
      ></path>
    </g>
  </svg>
</template>

<script>
export default {
  name: "PieChart",

  props: {
    parts: {
      required: true,
      type: Array,
    },
    size: {
      default: 32,
    },
  },

  data() {
    return {
      colors: ["#5ab1ef", "#fa6e86", "#ffb980", "#19d4ae", "#0067a6"],
    };
  },

  computed: {
    sizeSum() {
      return this.parts.map((item) => item.size).reduce((x, y) => x + y);
    },
    paths() {
      let out = [];
      let i = 0;
      let startSize = 0;
      const sizeToRel = (size) => (size / this.sizeSum) * Math.PI * 2;
      for (let item of this.parts) {
        let startX = Math.cos(sizeToRel(startSize));
        let startY = Math.sin(sizeToRel(startSize));
        let x = Math.cos(sizeToRel(startSize + item.size));
        let y = Math.sin(sizeToRel(startSize + item.size));
        out.push({
          startX: startX,
          startY: startY,
          endX: x,
          endY: y,
          longArc: item.size > 0.5 * this.sizeSum ? 1 : 0,
          color: item.color || this.colors[i % this.colors.length],
        });
        i++;
        startX = x;
        startY = y;
        startSize += item.size;
      }
      return out;
    },
  },
};
</script>
