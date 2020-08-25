<template>
<CheckMark
        trueColor="success"
        falseColor="error"
        trueIcon="fa-check"
        falseIcon="fa-times"
        value="value"
        />
</template>

<script>

import CheckMark from '@/components/util/CheckMark'

export default {
name: "GoodBadMark",
  components: {CheckMark}
}
</script>

<style scoped>

</style>
