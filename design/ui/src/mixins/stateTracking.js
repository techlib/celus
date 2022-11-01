import isEqual from "lodash/isEqual";
import { fromBase64Object, toBase64Object } from "@/libs/serialization";

export default {
  data() {
    return {
      watchedAttrs: [],
    };
  },

  computed: {
    trackedState: {
      // this is a default implementation of `trackedState` which uses
      // a list of `watchedAttrs` to determine which attributes to track.
      // If you want to customize the tracked state, you can override
      // this computed property in your component - this way you can modify
      // for the serialization and de-serialization steps.
      //
      // In this implementation, you should set `alwaysTrack` to true
      // for attributes which have non-empty default values, otherwise
      // an empty value will not be stored in the URL and when loaded,
      // the default value will be used instead.
      //
      // It is also possibile to rename the attribute in the URL by
      // providing the `var` attribute in the `watchedAttrs` list.
      // This is useful when you want to use a shorter name in the URL
      // or when you do not want to expose the internal name of the attribute.
      get() {
        let out = {};
        this.watchedAttrs.forEach((attr) => {
          if (
            (this[attr.name] && this[attr.name].length !== 0) ||
            attr.alwaysTrack
            // to have only non-empty parameters in the url
          ) {
            out[attr.var || attr.name] = this[attr.name];
          }
        });
        return out;
      },
      set(val) {
        this.watchedAttrs.forEach((attr) => {
          // the key could be in the .var attr, if not, use the .name
          const key = attr.var || attr.name;
          const value = val[key];
          if (value !== undefined) {
            switch (attr.type) {
              case Object:
                this[attr.name] = value;
                break;
              case Array:
                this[attr.name] = value;
                break;
              case String:
                this[attr.name] = String(value);
                break;
              case Number:
                this[attr.name] = parseInt(value);
                break;
              case Boolean:
                this[attr.name] = value === "true";
                break;
              default:
                this[attr.name] = value;
                console.warn(
                  `the attribute \`type\` of item \`${attr.name}\` in \`watchedAttrs\` has not been recognized, thus the \`trackedState\` might not be working properly.`
                );
            }
          }
        });
      },
    },
  },

  methods: {
    restoreTrackedState() {
      console.debug("restoring state from query", this.$route.query);
      this.trackedState = fromBase64Object(this.$route.query);
    },
  },

  mounted() {
    this.restoreTrackedState();
  },

  watch: {
    trackedState: {
      handler: function (newVal, oldVal) {
        if (!isEqual(newVal, oldVal)) {
          // push state to history
          console.debug("store state in history", newVal);
          history.replaceState(
            {},
            "",
            this.$router.resolve({
              path: this.$route.path,
              query: toBase64Object(newVal),
            }).href
          );
        }
      },
      deep: true,
    },
  },
};
