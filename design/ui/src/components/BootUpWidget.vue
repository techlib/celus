<i18n lang="yaml">
en:
  loading_basic_data: Loading basic data
  waiting_for_backend: Connecting to Celus server

# we use the English text for Czech on purpose - we do not want to accidentally show cs to
# English speakers.
cs:
  loading_basic_data: Loading basic data
  waiting_for_backend: Connecting to Celus server
</i18n>

<template>
  <div>
    <div class="bootup-logo">
      <img
        src="../assets/celus-plus-white-vertical-nobg.svg"
        height="158"
        alt="Celus Logo"
      />
    </div>
    <h1 class="bootup">Welcome to Celus</h1>
    <LoaderWidget
      :text="$t(bootUpMessage)"
      height="300px"
      padding-top="80px"
      max-width="400px"
    />
  </div>
</template>

<script>
import LoaderWidget from "@/components/util/LoaderWidget";
import { mapState } from "vuex";
export default {
  name: "BootUpWidget",

  components: { LoaderWidget },

  computed: {
    ...mapState({
      backendReady: "backendReady",
      bootUpMessage: "bootUpMessage",
    }),
  },
};
</script>

<style scoped lang="scss">
h1.bootup {
  text-align: center;
  font-size: 48px;
  color: #999999;
}

div.bootup-logo {
  padding-top: 10vh;
  text-align: center;
}
</style>
