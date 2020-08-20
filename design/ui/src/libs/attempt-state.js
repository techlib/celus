const ATTEMPT_UNKNOWN = 'unknown'
const ATTEMPT_SUCCESS = 'success'
const ATTEMPT_ERROR = 'error'
const ATTEMPT_QUEUED = 'queued'

function attemptState (attempt) {
  if (attempt.queued) {
    return ATTEMPT_QUEUED
  } else if (attempt.import_batch) {
    return ATTEMPT_SUCCESS
  } else if (attempt.error_code) {
    return ATTEMPT_ERROR
  }
  return ATTEMPT_UNKNOWN
}

export {
  attemptState,
  ATTEMPT_UNKNOWN,
  ATTEMPT_ERROR,
  ATTEMPT_SUCCESS,
  ATTEMPT_QUEUED,
}
