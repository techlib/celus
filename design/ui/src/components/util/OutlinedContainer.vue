<template>
  <div class="outlined-container">
    <div class="container-label">
      {{ label }}
    </div>
    <div class="label-spacer">
      {{ label }}
    </div>
    <slot />
  </div>
</template>

<script>
export default {
  props: {
    label: {
      type: String,
      required: true,
    },
  },
};
</script>

<style scoped lang="scss">
.outlined-container {
  border: 1px solid #00000020;
  border-radius: 10px;
  padding: 12px 12px 8px 12px;
  margin-bottom: 8px;
  margin-top: 8px;
  position: relative;
  display: inline-block;
  width: fit-content;
}

.outlined-container .container-label {
  position: absolute;
  top: -8px;
  left: 12px;
  background-color: white;
  padding: 0px 4px;
  font-size: 12px;
  color: rgba(0, 0, 0, 0.6);
  line-height: 16px;
  white-space: nowrap;
  pointer-events: none;
}

.outlined-container .label-spacer {
  visibility: hidden;
  height: 0;
  font-size: 12px;
  line-height: 0;
  padding: 0 4px;
  white-space: nowrap;
  margin-bottom: 0;
  overflow: hidden;
}
</style>
