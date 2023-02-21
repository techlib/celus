<template>
  <span>
    <span class="px-2 font-weight-light"
      >metric={{ definition.metric || "*" }}</span
    >
    <span class="px-2 font-weight-light">
      <span
        v-for="(value, name, index) in definition.filters"
        class="me-2"
        :style="{ color: palette[index % palette.length] }"
        :key="name"
      >
        {{ name }}={{ value.toString() }}
      </span>
    </span>
  </span>
</template>
<script>
export default {
  name: "ReportPartParams",
  props: {
    definition: { type: Object, required: true },
  },

  data() {
    return {
      palette: [
        "#009900",
        "#990099",
        "#0080FF",
        "#FF0080",
        "#000099",
        "#8000FF",
      ],
    };
  },
};
</script>
