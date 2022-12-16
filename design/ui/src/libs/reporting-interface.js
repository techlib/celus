import { monthsBetween, ymDateFormat } from "@/libs/dates";
import { toBase64JSON } from "@/libs/serialization";

class Report {
  constructor(
    $router,
    http,
    reportType,
    metric,
    filters = null,
    dateRangeStart = null,
    dateRangeEnd = null,
    organizationId = null
  ) {
    this.$router = $router;
    this.http = http;
    this.reportType = reportType;
    this.metric = metric;
    this.filters = filters || {};
    this.data = [];
    this.metricId = null;
    this.resolvedFilters = {};
    this.filtersResolved = false;
    this.dateRangeStart = dateRangeStart;
    this.dateRangeEnd = dateRangeEnd;
    this.organizationId = organizationId;
  }

  // properties

  get allReady() {
    // do we have everything we need to make a request?
    return (
      this.reportType && (this.metricId || !this.metric) && this.filtersResolved
    );
  }
  get slicerUrl() {
    let groups = ["date"];
    // some implicit filters
    let filters = {
      report_type: [this.reportType.pk],
      metric: this.metric ? [this.metricId] : undefined,
      date: { start: this.dateRangeStart, end: this.dateRangeEnd },
    };
    if (this.organizationId) {
      filters.organization = [this.organizationId];
    }
    // explicit filters
    Object.entries(this.resolvedFilters).forEach(([key, value]) => {
      filters[key] = value;
    });
    // put it all together
    let params = {
      primary_dimension: "platform",
      page: 1,
      page_size: 1000,
      zero_rows: true,
      groups: toBase64JSON(groups),
      filters: toBase64JSON(filters),
    };
    return this.$router.resolve({
      path: "/api/flexible-slicer/",
      query: params,
    }).href;
  }

  get dateRange() {
    // returns the months between the first and last date as set in the app preferences
    return monthsBetween(this.dateRangeStart, this.dateRangeEnd).map(
      ymDateFormat
    );
  }

  get total() {
    let total = 0;
    this.data.forEach((item) => {
      this.dateRange.forEach((date) => {
        total += item[`grp-${date}-01`] ?? 0;
      });
    });
    return total;
  }

  // methods

  async loadAllData() {
    await Promise.all([this.resolveMetric(), this.resolveFilters()]);
    await this.loadMainData();
  }

  async loadMainData() {
    if (!this.allReady) {
      console.warn("not ready to load data");
      return;
    }
    let result = await this.http({ url: this.slicerUrl });
    this.data = result.response.data.results;
  }

  async resolveMetric() {
    if (!this.metric) {
      this.metricId = null;
      return;
    }
    let result = await this.http({
      url: "/api/metric/",
    });
    if (!result.error) {
      const metric = result.response.data.find(
        (metric) => metric.short_name === this.metric
      );
      if (metric) {
        this.metricId = metric.pk;
      } else {
        console.error("Metric not found", this.metric);
      }
    }
  }

  async resolveFilters() {
    for (let [name, value] of Object.entries(this.filters)) {
      // find the dimension in the report type
      const idx = this.reportType.dimensions_sorted.findIndex(
        (dimension) => dimension.short_name === name
      );
      if (idx === -1) {
        console.error("Dimension not found", name);
        continue;
      }
      const dimName = `dim${idx + 1}`;
      let result = await this.http({
        url: "/api/dimension-text/",
        params: { dimension: this.reportType.dimensions_sorted[idx].pk },
      });
      if (!result.error) {
        function translate(val) {
          const dimensionValue = result.response.data.results.find(
            (dimensionValue) => dimensionValue.text === val
          );
          if (dimensionValue) {
            return dimensionValue.pk;
          } else {
            console.error("Dimension value not found", val);
          }
        }
        if (Array.isArray(value)) {
          this.resolvedFilters[dimName] = value
            .map(translate)
            .filter((val) => val);
        } else {
          this.resolvedFilters[dimName] = [translate(value)];
        }
      }
    }
    this.filtersResolved = true;
  }

  async changeDateRange(dateRangeStart, dateRangeEnd) {
    this.dateRangeStart = dateRangeStart;
    this.dateRangeEnd = dateRangeEnd;
    await this.loadMainData();
  }

  async changeOrganizationId(organizationId) {
    this.organizationId = organizationId;
    await this.loadMainData();
  }
}

export default Report;
