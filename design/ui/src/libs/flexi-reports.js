import { implicitDimensions } from "@/mixins/dimensions";
import axios from "axios";
import { toBase64JSON } from "@/libs/serialization";

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
    this.pk = null;
    this.names = {};
  }

  static fromObject(ref, data) {
    let dim = new Dimension(ref);
    dim.shortName = data.short_name;
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
    return this.isExplicit || !this.ref.startsWith("date");
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
    this.splitBy = null;
    this.name = "";
    this.owner = null;
    this.ownerOrganization = null;
    this.includeZeroRows = false;
    this.tagRollUp = false;
    this._tagDimension = new Dimension("tag");
    this._tagDimension.shortName = "tag";
    this._tagDimension.name = "labels.tag";
    this.tagClass = null;
  }

  get accessLevel() {
    return this.owner ? "user" : this.ownerOrganization ? "org" : "sys";
  }

  get accessLevelIcon() {
    return FlexiReport.accessLeveLToIcon[this.accessLevel];
  }

  get effectivePrimaryDimension() {
    return this.tagRollUp ? this._tagDimension : this.primaryDimension;
  }

  canEdit(user, organizationMap) {
    // returns a Boolean if the user can edit this report
    if (this.owner && this.owner === user.pk) {
      return true;
    }
    if (user.is_superuser || user.is_admin_of_master_organization) {
      return true;
    }
    if (this.ownerOrganization) {
      let org = organizationMap[this.ownerOrganization];
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
        let res = {
          dimension: this.resolveDim(item.dimension),
        };
        if (item.values) res["values"] = item.values;
        if (item.start) res["start"] = item.start;
        if (item.end) res["end"] = item.end;
        if (item.tag_ids) res["tag_ids"] = item.tag_ids;
        return res;
      });
    // group by
    this.groupBy = config.group_by.map((item) => this.resolveDim(item));
    // order by
    this.orderBy = config.order_by;
    // split by
    // in this case the backend supports split_by as a list (for splitting by
    // more than one dimension), but we do not use it in the UI and just use
    // single dimension - here we convert between the list and a single value
    this.splitBy =
      config.split_by && config.split_by.length
        ? this.resolveDim(config.split_by[0])
        : null;
    // extra params
    this.includeZeroRows = config.zero_rows ?? false;
    this.tagRollUp = config.tag_roll_up ?? false;
    this.tagClass = config.tag_class ?? null;
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

  urlParams(filterOverride = null) {
    let filters = {};
    this.filters.forEach((item) => {
      if (item.start || item.end) {
        filters[item.dimension.ref] = { start: item.start, end: item.end };
      } else if (item.tag_ids) {
        filters["tag__" + item.dimension.ref] = item.tag_ids;
      } else {
        filters[item.dimension.ref] = item.values;
      }
    });
    filters["report_type"] = this.reportTypes.map((item) => item.pk);
    if (filterOverride) {
      filters = { ...filters, ...filterOverride };
    }
    return {
      primary_dimension: this.primaryDimension.ref,
      filters: toBase64JSON(filters),
      groups: toBase64JSON(this.groupBy.map((item) => item.ref)),
      split_by: this.splitBy ? toBase64JSON([this.splitBy.ref]) : null,
      order_by: this.orderBy.join(";"),
      zero_rows: this.includeZeroRows,
      tag_roll_up: this.tagRollUp,
      tag_class: this.tagClass,
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

  async startExport(format) {
    let resp = await axios.post("/api/export/flexible-export/", {
      ...this.urlParams(),
      format: format,
      name: this.name,
    });
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

  static formatToText = {
    XLSX: "Excel",
    ZIP_CSV: "CSV",
  };

  constructor() {
    this.pk = null;
    this.name = "";
    this.primaryDimension = null;
    this.reportTypes = []; // these are filters as well, but we treat is differently
    this.filters = [];
    this.groupBy = [];
    this.orderBy = [];
    this.outputFile = null;
    this.fileFormat = null;
    this.fileSize = 0;
    this.status = 0;
    this.errorInfo = {};
  }

  static async fromAPIObject(data, allReportTypes = null) {
    let flexiExport = new FlexiExport();
    flexiExport.pk = data.pk;
    flexiExport.outputFile = data.output_file;
    flexiExport.created = data.created;
    flexiExport.fileSize = data.file_size;
    flexiExport.fileFormat = this.formatToText[data.file_format];
    flexiExport.status = data.status;
    flexiExport.errorInfo = data.error_info;
    flexiExport.name = data.name;
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
