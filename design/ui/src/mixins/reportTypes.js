import { getNamedObjectSorter } from "@/libs/sorting";
import axios from "axios";
import { Dimension } from "@/libs/flexi-reports";

export default {
  data() {
    return {
      allReportTypes: [],
      reportTypeMap: new Map(),
    };
  },

  computed: {
    reportTypesUrl() {
      return `/api/report-type/?nonzero-only`;
    },
  },

  methods: {
    async fetchReportTypes() {
      try {
        let resp = await axios.get(this.reportTypesUrl);
        this.allReportTypes = resp.data.sort(
          getNamedObjectSorter(this.$i18n.locale)
        );
        this.allReportTypes.forEach((rt) => {
          rt.dimensions_sorted.forEach((dim, idx) => {
            dim.id = `dim${idx + 1}`;
          });
          rt.dimensionObjs = rt.dimensions_sorted.map((dim) => {
            let obj = Dimension.fromObject(dim.id, dim);
            obj.name = obj.getName(this.$i18n);
            return obj;
          });
        });
        let rtMap = new Map();
        this.allReportTypes.forEach((rt) => rtMap.set(rt.pk, rt));
        this.reportTypeMap = rtMap;
      } catch (error) {
        this.showSnackbar({
          content: "Could not report types: " + error,
          color: "error",
        });
      }
    },
  },
};
