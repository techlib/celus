<template>
  <ul>
    <li v-for="IPv4Address in this.harvesterIPv4Addresses" :key="IPv4Address">
      {{ IPv4Address }} (IPv4)
    </li>
    <li v-for="IPv6Address in this.harvesterIPv6Addresses" :key="IPv6Address">
      {{ IPv6Address }} (IPv6)
    </li>
  </ul>
</template>
<script>
import { mapGetters } from "vuex";

export default {
  name: "HarvesterIPAddressList",

  computed: {
    ...mapGetters({
      harvesterIPv4Addresses: "harvesterIPv4Addresses",
      harvesterIPv6Addresses: "harvesterIPv6Addresses",
    }),
  },
};
</script>
