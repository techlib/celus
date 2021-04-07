let implicitDimensions = [
  {
    shortName: "organization",
    nameKey: "organization",
  },
  {
    shortName: "platform",
    nameKey: "labels.platform",
  },
  {
    shortName: "target",
    nameKey: "labels.title",
  },
  {
    shortName: "metric",
    nameKey: "labels.metric",
  },
  {
    shortName: "date",
    nameKey: "labels.year_and_month",
  },
  {
    shortName: "date__year",
    nameKey: "labels.year",
  },
];

let dimensionMixin = {
  data() {
    let dimensions = [];
    let dimensionToTitle = new Map();
    implicitDimensions.forEach(item => {
      dimensions.push({ id: item.shortName, name: this.$t(item.nameKey) });
      dimensionToTitle.set(item.shortName, this.$t(item.nameKey));
    });
    return {
      dimensions,
      dimensionToTitle,
    };
  },
};

export { dimensionMixin, implicitDimensions };
