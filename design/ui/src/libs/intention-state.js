import { parseDateTime } from "@/libs/dates";
import {
  ATTEMPT_AWAITING_IMPORT,
  ATTEMPT_ERROR,
  attemptState,
  attemptStateToIcon,
} from "@/libs/attempt-state";

function annotateIntention(intention) {
  intention.isRetry = !!(
    intention.data_not_ready_retry ||
    intention.service_not_available_retry ||
    intention.service_busy_retry
  );

  intention.notBefore = parseDateTime(intention.not_before);
  intention.whenProcessed = parseDateTime(intention.when_processed);
  intention.endDate = parseDateTime(intention.end_date);
  intention.attemptDeleted = !!(intention.when_processed && !intention.attempt);
  intention.hasAttempt = !!intention.attempt;
  intention.fetchingData = intention.fetching_data;
  intention.importing =
    intention.hasAttempt &&
    attemptState(intention.attempt) === ATTEMPT_AWAITING_IMPORT;
  intention.isFinished =
    !!(intention.hasAttempt || intention.whenProcessed) && !intention.importing;
  intention.brokenCredentials = !!intention.broken_credentials;

  // let's deal with the case the intention is duplicate of some other intention
  // we copy most of the attributes from the target intention to this one
  intention.isDuplicate = !!intention.duplicate_of;
  if (intention.duplicate_of) {
    annotateIntention(intention.duplicate_of);
    intention.isFinished = intention.duplicate_of.isFinished;
    intention.fetchingData = intention.duplicate_of.fetchingData;
    intention.hasAttempt = intention.duplicate_of.hasAttempt;
    intention.attempt = intention.duplicate_of.attempt;
    intention.attemptDeleted = intention.duplicate_of.attemptDeleted;
    intention.whenProcessed = intention.duplicate_of.whenProcessed;
    intention.notBefore = intention.duplicate_of.notBefore;
    intention.brokenCredentials = intention.duplicate_of.brokenCredentials;
  }

  if (!intention.hasAttempt) {
    intention.previousAttempt =
      intention.previous_intention && intention.previous_intention.attempt;
  }
  intention.state = intentionState(intention);

  intention.isForceRunPossible =
    intention.notBefore > new Date() && // skip already planned
    intention.endDate < new Date() && // skip for future data
    (intention.state === INTENTION_WAITING ||
      intention.state === INTENTION_QUEUED);
  intention.isCancelPossible =
    intention.state === INTENTION_WAITING ||
    intention.state === INTENTION_QUEUED;
  intention.isCanceled = intention.state === INTENTION_CANCELED;
  intention.loading = false;
}

const INTENTION_RUNNING = "running";
const INTENTION_DELETED = "deleted";
const INTENTION_BROKEN = "broken_sushi";
const INTENTION_WAITING = "waiting";
const INTENTION_QUEUED = "queued";
const INTENTION_CANCELED = "canceled";

function intentionState(intention) {
  if (intention.fetchingData) {
    return INTENTION_RUNNING;
  }
  if (intention.brokenCredentials) {
    return INTENTION_BROKEN;
  }
  if (intention.attempt) {
    const as = attemptState(intention.attempt);
    if (as === ATTEMPT_ERROR && intention.attempt.error_code === "3031")
      return INTENTION_WAITING;
    else return as;
  }
  if (intention.canceled) {
    return INTENTION_CANCELED;
  }
  if (intention.attemptDeleted) {
    return INTENTION_DELETED;
  }
  if (intention.isRetry) {
    return INTENTION_QUEUED;
  }
  return INTENTION_WAITING;
}

function intentionStateToIcon(state) {
  switch (state) {
    case INTENTION_RUNNING:
      return { icon: "fa-spinner fa-spin", color: "blue" };
    case INTENTION_DELETED:
      return { icon: "fa-trash", color: "secondary" };
    case INTENTION_BROKEN:
      return { icon: "fa-bug", color: "error" };
    case INTENTION_QUEUED:
      return { icon: "far fa-pause-circle", color: "secondary" };
    case INTENTION_WAITING:
      return { icon: "far fa-clock", color: "secondary" };
    case INTENTION_CANCELED:
      return { icon: "fas fa-ban", color: "error" };
    default:
      return attemptStateToIcon(state);
  }
}

export {
  annotateIntention,
  intentionState,
  intentionStateToIcon,
  INTENTION_QUEUED,
  INTENTION_CANCELED,
  INTENTION_RUNNING,
  INTENTION_DELETED,
  INTENTION_BROKEN,
  INTENTION_WAITING,
};
