const ATTEMPT_UNKNOWN = "unknown";
const ATTEMPT_SUCCESS = "success";
const ATTEMPT_ERROR = "error";
const ATTEMPT_NOT_MADE = "missing";
const ATTEMPT_EMPTY_DATA = "empty_data";
const ATTEMPT_PARTIAL_DATA = "partial_data";
const ATTEMPT_IMPORT_FAILED = "import_failed";
const ATTEMPT_AWAITING_IMPORT = "awaiting_import";
const ATTEMPT_CANCELED = "canceled";
const BROKEN_CREDENTIALS = "broken";
const BROKEN_REPORT = "broken_report";

function attemptState(attempt) {
  if (attempt.status == "untried") {
    // untried is status only for monthly overview
    return ATTEMPT_NOT_MADE;
  } else if (attempt.status == "import_failed") {
    return ATTEMPT_IMPORT_FAILED;
  } else if (attempt.import_batch) {
    if (attempt.partial_data) {
      return ATTEMPT_PARTIAL_DATA;
    }
    return ATTEMPT_SUCCESS;
  } else if (attempt.error_code) {
    if (attempt.error_code === "3030" && attempt.status == "no_data") {
      return ATTEMPT_EMPTY_DATA;
    }
    return ATTEMPT_ERROR;
  } else if (attempt.status == "importing") {
    return ATTEMPT_AWAITING_IMPORT;
  } else if (attempt.status == "no_data") {
    return ATTEMPT_EMPTY_DATA;
  } else if (attempt.status == "canceled" || attempt.status == "unprocessed") {
    return ATTEMPT_CANCELED;
  }
  return ATTEMPT_UNKNOWN;
}

function attemptStateToIcon(state) {
  switch (state) {
    case ATTEMPT_NOT_MADE:
      return { color: "secondary", icon: "far fa-clock" };
    case ATTEMPT_SUCCESS:
      return { color: "success", icon: "far fa-check-circle" };
    case ATTEMPT_EMPTY_DATA:
      return { color: "success", icon: "far fa-circle" };
    case ATTEMPT_ERROR:
      return { color: "red lighten-2", icon: "fa-exclamation-circle" };
    case ATTEMPT_AWAITING_IMPORT:
      return { color: "blue", icon: "fa-cog fa-spin" };
    case ATTEMPT_IMPORT_FAILED:
      return { color: "error", icon: "fa-cog" };
    case ATTEMPT_PARTIAL_DATA:
      return { color: "warning", icon: "fas fa-exclamation-triangle" };
    default:
      return { color: "warning", icon: "far fa-question-circle" };
  }
}

export {
  attemptState,
  attemptStateToIcon,
  ATTEMPT_UNKNOWN,
  ATTEMPT_ERROR,
  ATTEMPT_IMPORT_FAILED,
  ATTEMPT_SUCCESS,
  ATTEMPT_AWAITING_IMPORT,
  ATTEMPT_NOT_MADE,
  ATTEMPT_EMPTY_DATA,
  ATTEMPT_PARTIAL_DATA,
  ATTEMPT_CANCELED,
  BROKEN_CREDENTIALS,
  BROKEN_REPORT,
};
