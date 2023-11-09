import IdTranslation from "@/libs/id-translation";

export default {
  data() {
    let explicitDimensionTranslator = new IdTranslation("/api/dimension-text/");
    return {
      translators: {
        metric: new IdTranslation("/api/metric/"),
        organization: new IdTranslation("/api/organization/"),
        platform: new IdTranslation("/api/platform/"),
        target: new IdTranslation("/api/title/"),
        report_type: new IdTranslation("/api/report-type/"),
        explicitDimension: explicitDimensionTranslator,
        tag: new IdTranslation("/api/tags/tag/"),
        tagClass: new IdTranslation("/api/tags/tag-class/visible-tags/"),
        dim1: null,
        dim2: null,
        dim3: null,
        dim4: null,
        dim5: null,
        dim6: null,
        dim7: null,
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
