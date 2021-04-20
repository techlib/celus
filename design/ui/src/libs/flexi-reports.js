import { implicitDimensions } from "@/mixins/dimensions";
import axios from "axios";

class Dimension {
  /*
  ref - how is this dimension referred to from the report type

  There can be two types of dimension - implicit and explicit:

  * for implicit, just the `ref` is enough, the rest can be deduced or
    has no meaning (like pk). We use `fromImplicit` for this.
  * for explicit, we need to load the data from an API record which is done
    in `fromObject`.

  As for names, either the `names` attr is filled with {lang->name} values
  or we use the `name` attribute which should contain a key for translation
  (not the translated string itself) of the name
   */
  constructor(ref = "") {
    this.ref = ref;
    this.shortName = "";
    this.name = "";
    this.type = null;
    this.pk = null;
    this.names = {};
  }

  static fromObject(ref, data) {
    let dim = new Dimension(ref);
    dim.shortName = data.short_name;
    dim.type = data.type;
    dim.pk = data.pk;
    dim.names = {};
    Object.entries(data)
      .filter(([k, v]) => k.startsWith("name_"))
      .forEach(([k, v]) => (dim.names[k.substring(5)] = v));
    return dim;
  }

  static fromImplicit(ref) {
    let dim = new Dimension(ref);
    dim.shortName = ref;
    let dimRec = implicitDimensions.find((item) => item.shortName === dim.ref);
    if (dimRec) dim.name = dimRec.nameKey;
    return dim;
  }

  static isNameExplicit(name) {
    return name.startsWith("dim");
  }

  static explicitIndex(ref) {
    // index number of the dimension in a report type
    let dimMatch = /dim(\d)/.exec(ref);
    if (dimMatch) {
      return Number.parseInt(dimMatch[1]) - 1;
    }
    return null;
  }

  get isExplicit() {
    return Dimension.isNameExplicit(this.ref);
  }

  get isMapped() {
    // are the values mapped through a pk->value translator?
    return (
      (this.isExplicit && this.type === 2) ||
      (!this.isExplicit && !this.ref.startsWith("date"))
    );
  }

  getName(i18n) {
    if (this.names && this.names[i18n.locale]) {
      return this.names[i18n.locale];
    }
    if (this.name) {
      return i18n.t(this.name);
    }
    return this.shortName;
  }
}

class FlexiReport {
  static accessLeveLToIcon = {
    sys: "fa-globe",
    org: "fa-university",
    user: "fa-user",
  };

  constructor() {
    this.pk = null;
    this.primaryDimension = null;
    this.reportTypes = []; // these are filters as well, but we treat is differently
    this.filters = [];
    this.groupBy = [];
    this.orderBy = [];
    this.name = "";
    this.owner = null;
    this.ownerOrganization = null;
  }

  get accessLevel() {
    return this.owner ? "user" : this.ownerOrganization ? "org" : "sys";
  }

  get accessLevelIcon() {
    return FlexiReport.accessLeveLToIcon[this.accessLevel];
  }

  canEdit(user, organizationMap) {
    // returns a Boolean if the user can edit this report
    if (this.owner && this.owner === user.pk) {
      return true;
    }
    if (user.is_superuser || user.is_from_master_organization) {
      return true;
    }
    console.log("org", this.ownerOrganization);
    if (this.ownerOrganization) {
      let org = organizationMap[this.ownerOrganization];
      console.log("org2", org, org.is_admin);
      if (org && org.is_admin) {
        return true;
      }
    }
    return false;
  }

  static async fromAPIObject(data, allReportTypes = null) {
    let report = new FlexiReport();
    report.pk = data.pk;
    report.name = data.name;
    report.owner = data.owner;
    report.ownerOrganization = data.owner_organization;
    await report.readConfig(data.config, allReportTypes);
    return report;
  }

  async readConfig(config, allReportTypes = null) {
    // when `allReportTypes` is given, it has to be a Map of id->reportType
    // report types first as we need them later on to remap dimensions
    let rtFilter = config.filters.find(
      (item) => item.dimension === "report_type"
    );
    if (rtFilter) {
      for (let rtId of rtFilter.values) {
        this.reportTypes.push(
          await this.resolveReportType(rtId, allReportTypes)
        );
      }
    }
    // primary dimension
    this.primaryDimension = this.resolveDim(config.primary_dimension);
    // filters
    this.filters = config.filters
      .filter((item) => item.dimension !== "report_type")
      .map((item) => {
        return {
          values: item.values,
          dimension: this.resolveDim(item.dimension),
        };
      });
    // group by
    this.groupBy = config.group_by.map((item) => this.resolveDim(item));
    // order by
    this.orderBy = config.order_by;
  }

  async resolveReportType(id, allReportTypes = null) {
    if (allReportTypes) {
      return allReportTypes.get(id);
    }
    return (await axios.get(`/api/report-type/${id}/`)).data;
  }

  resolveDim(ref) {
    if (!Dimension.isNameExplicit(ref)) {
      return Dimension.fromImplicit(ref);
    }
    // we have an explicit dimension, we need to run is through report type
    // to see what it is
    let idx = Dimension.explicitIndex(ref);
    if (idx !== null) {
      // we have an explicit dimension - we need to resolve it using the report_type, etc.
      if (this.reportTypes.length === 1) {
        return Dimension.fromObject(
          ref,
          this.reportTypes[0].dimensions_sorted[idx]
        );
      }
    }
    return new Dimension(ref);
  }

  urlParams() {
    let filters = {};
    this.filters.forEach((item) => (filters[item.dimension.ref] = item.values));
    filters["report_type"] = this.reportTypes.map((item) => item.pk);
    return {
      primary_dimension: this.primaryDimension.ref,
      filters: btoa(JSON.stringify(filters)),
      groups: btoa(JSON.stringify(this.groupBy.map((item) => item.ref))),
      order_by: this.orderBy.join(";"),
    };
  }

  async save() {
    let data = {
      name: this.name,
      config: this.urlParams(),
      owner: this.owner,
      owner_organization: this.ownerOrganization,
    };
    if (this.pk) {
      await axios.patch(`/api/flexible-report/${this.pk}/`, data);
    } else {
      let resp = await axios.post("/api/flexible-report/", data);
      this.pk = resp.data.pk;
    }
  }

  async rename(newName) {
    this.name = newName;
    if (this.pk) {
      await axios.patch(`/api/flexible-report/${this.pk}/`, { name: newName });
    }
  }

  async startExport() {
    let resp = await axios.post(
      "/api/export/flexible-export/",
      this.urlParams()
    );
    return resp.data;
  }
}

const EXPORT_ERROR = 3;
const EXPORT_FINISHED = 2;
const EXPORT_IN_PROGRESS = 1;
const EXPORT_NOT_STARTED = 0;

class FlexiExport {
  static statusToText = {
    0: "not_started",
    1: "in_progress",
    2: "finished",
    3: "error",
  };

  constructor() {
    this.pk = null;
    this.primaryDimension = null;
    this.reportTypes = []; // these are filters as well, but we treat is differently
    this.filters = [];
    this.groupBy = [];
    this.orderBy = [];
    this.outputFile = null;
    this.status = 0;
    this.errorInfo = {};
  }

  static async fromAPIObject(data, allReportTypes = null) {
    let flexiExport = new FlexiExport();
    flexiExport.pk = data.pk;
    flexiExport.outputFile = data.output_file;
    flexiExport.created = data.created;
    flexiExport.fileSize = data.file_size;
    flexiExport.status = data.status;
    flexiExport.errorInfo = data.error_info;
    await flexiExport.readConfig(data.export_params, allReportTypes);
    return flexiExport;
  }

  get statusText() {
    return FlexiExport.statusToText[this.status];
  }

  async readConfig(config, allReportTypes = null) {
    // when `allReportTypes` is given, it has to be a Map of id->reportType
    // report types first as we need them later on to remap dimensions
    let rtFilter = config.filters.find(
      (item) => item.dimension === "report_type"
    );
    if (rtFilter) {
      for (let rtId of rtFilter.values) {
        this.reportTypes.push(
          await this.resolveReportType(rtId, allReportTypes)
        );
      }
    }
    // primary dimension
    this.primaryDimension = this.resolveDim(config.primary_dimension);
    // filters
    this.filters = config.filters
      .filter((item) => item.dimension !== "report_type")
      .map((item) => {
        return {
          values: item.values,
          dimension: this.resolveDim(item.dimension),
        };
      });
    // group by
    this.groupBy = config.group_by.map((item) => this.resolveDim(item));
    // order by
    this.orderBy = config.order_by;
  }

  async resolveReportType(id, allReportTypes = null) {
    if (allReportTypes) {
      return allReportTypes.get(id);
    }
    return (await axios.get(`/api/report-type/${id}/`)).data;
  }

  resolveDim(ref) {
    if (!Dimension.isNameExplicit(ref)) {
      return Dimension.fromImplicit(ref);
    }
    // we have an explicit dimension, we need to run is through report type
    // to see what it is
    let idx = Dimension.explicitIndex(ref);
    if (idx !== null) {
      // we have an explicit dimension - we need to resolve it using the report_type, etc.
      if (this.reportTypes.length === 1) {
        return Dimension.fromObject(
          ref,
          this.reportTypes[0].dimensions_sorted[idx]
        );
      }
    }
    return new Dimension(ref);
  }
}

export {
  Dimension,
  FlexiReport,
  FlexiExport,
  EXPORT_ERROR,
  EXPORT_FINISHED,
  EXPORT_IN_PROGRESS,
  EXPORT_NOT_STARTED,
};
