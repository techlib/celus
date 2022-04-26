import color from "color";

export default {
  data() {
    return {
      bgColor: "#3F51B5",
      //textColor: "#303030",  // text color was switched to computed for now
      defaultDarkColor: color("#303030"),
      defaultLightColor: color("#FFFFFF"),
    };
  },

  computed: {
    threshLuminosity() {
      return (
        (this.defaultLightColor.luminosity() +
          this.defaultDarkColor.luminosity()) /
        2
      );
    },
    textColor() {
      if (color(this.bgColor).luminosity() > this.threshLuminosity) {
        return this.defaultDarkColor.hex();
      }
      return this.defaultLightColor.hex();
    },
  },
};
