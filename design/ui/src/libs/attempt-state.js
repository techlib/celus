const ATTEMPT_UNKNOWN = "unknown";
const ATTEMPT_SUCCESS = "success";
const ATTEMPT_ERROR = "error";
const ATTEMPT_QUEUED = "queued";
const ATTEMPT_NOT_MADE = "missing";
const ATTEMPT_EMPTY_DATA = "empty_data";
const BROKEN_CREDENTIALS = "broken";
const BROKEN_REPORT = "broken_report";

function attemptState(attempt) {
  if (attempt.untried) {
    return ATTEMPT_NOT_MADE;
  } else if (attempt.queued) {
    return ATTEMPT_QUEUED;
  } else if (attempt.import_batch) {
    return ATTEMPT_SUCCESS;
  } else if (attempt.error_code) {
    if (attempt.error_code === "3030" && attempt.processing_success) {
      return ATTEMPT_EMPTY_DATA;
    }
    return ATTEMPT_ERROR;
  }
  return ATTEMPT_UNKNOWN;
}

export {
  attemptState,
  ATTEMPT_UNKNOWN,
  ATTEMPT_ERROR,
  ATTEMPT_SUCCESS,
  ATTEMPT_QUEUED,
  ATTEMPT_NOT_MADE,
  ATTEMPT_EMPTY_DATA,
  BROKEN_CREDENTIALS,
  BROKEN_REPORT,
};
