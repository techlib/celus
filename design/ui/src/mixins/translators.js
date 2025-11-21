import { explicitDimensions } from "@/libs/dimensions";
import IdTranslation from "@/libs/id-translation";

export default {
  data() {
    let explicitDimensionTranslator = new IdTranslation("/api/dimension-text/");
    // null translators for all explicit dimensions
    let expTranslators = {};
    explicitDimensions.forEach((dim) => (expTranslators[dim] = null));
    return {
      translators: {
        metric: new IdTranslation("/api/metric/"),
        organization: new IdTranslation("/api/organization/"),
        platform: new IdTranslation("/api/platform/"),
        target: new IdTranslation("/api/title/"),
        item: new IdTranslation("/api/item/"),
        report_type: new IdTranslation("/api/report-type/"),
        explicitDimension: explicitDimensionTranslator,
        tag: new IdTranslation("/api/tags/tag/"),
        tagClass: new IdTranslation("/api/tags/tag-class/visible-tags/"),
        ...expTranslators,
      },
    };
  },

  methods: {
    getTranslator(dim) {
      if (dim.isMapped) {
        return dim.isExplicit
          ? this.translators.explicitDimension
          : this.translators[dim.ref];
      }
      return null;
    },
  },
};
