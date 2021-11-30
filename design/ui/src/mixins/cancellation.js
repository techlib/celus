/**
 * Usage:
 *
 * import cancellation from "@/mixins/cancellation";
 *
 * mixins: [cancellation],
 *
 * this.$store.dispatch("action", { component: this._cid, … })
 *
 * // or with '@/libs/http
 *
 * await http({url, component: this._cid})
 */

import http from "@/libs/http";
import { randomString } from "@/libs/strings";

export default {
  beforeCreate() {
    // Component ID, to avoid using private attribute this._uid
    // Eg.: DashboardPage-n4hl2wq7
    this._cid = `${this.$options.name}-${randomString(8)}`;
  },

  beforeMount() {
    this.$store.dispatch("cancellation/setup", this._cid);
  },

  beforeDestroy() {
    this.$store.dispatch("cancellation/cancel", this._cid);
  },

  methods: {
    http: async function (request) {
      return await http({ ...request, component: this._cid });
    },
  },
};
