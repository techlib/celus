const ATTEMPT_UNKNOWN = "unknown";
const ATTEMPT_SUCCESS = "success";
const ATTEMPT_ERROR = "error";
const ATTEMPT_QUEUED = "queued";
const ATTEMPT_NOT_MADE = "missing";
const ATTEMPT_EMPTY_DATA = "empty_data";
const ATTEMPT_PARTIAL_DATA = "partial_data";
const ATTEMPT_IMPORT_FAILED = "import_failed";
const BROKEN_CREDENTIALS = "broken";
const BROKEN_REPORT = "broken_report";
const ATTEMPT_AWAITING_IMPORT = "awaiting_import";

function attemptState(attempt) {
  if (attempt.status == "untried") {
    return ATTEMPT_NOT_MADE;
  } else if (attempt.queued) {
    return ATTEMPT_QUEUED;
  } else if (attempt.import_crashed) {
    return ATTEMPT_IMPORT_FAILED;
  } else if (attempt.import_batch) {
    if (attempt.partial_data) {
      return ATTEMPT_PARTIAL_DATA;
    }
    return ATTEMPT_SUCCESS;
  } else if (attempt.error_code) {
    if (attempt.error_code === "3030" && attempt.processing_success) {
      return ATTEMPT_EMPTY_DATA;
    }
    return ATTEMPT_ERROR;
  } else if (attempt.contains_data) {
    // contains data, but no import_batch - it is not yet imported
    return ATTEMPT_AWAITING_IMPORT;
  }
  return ATTEMPT_UNKNOWN;
}

function attemptStateToIcon(state) {
  switch (state) {
    case ATTEMPT_NOT_MADE:
      return { color: "secondary", icon: "far fa-clock" };
    case ATTEMPT_QUEUED:
      return { color: "secondary", icon: "far fa-pause-circle" };
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
  ATTEMPT_SUCCESS,
  ATTEMPT_QUEUED,
  ATTEMPT_AWAITING_IMPORT,
  ATTEMPT_NOT_MADE,
  ATTEMPT_EMPTY_DATA,
  ATTEMPT_PARTIAL_DATA,
  BROKEN_CREDENTIALS,
  BROKEN_REPORT,
};
