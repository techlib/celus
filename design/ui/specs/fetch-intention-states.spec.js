import {
  intentionState,
  INTENTION_RUNNING,
  INTENTION_WAITING,
  INTENTION_QUEUED,
  INTENTION_DELETED,
  INTENTION_CANCELED,
  INTENTION_BROKEN,
} from "@/libs/intention-state";

import { ATTEMPT_EMPTY_DATA } from "@/libs/attempt-state";

const cases_without_credentials = [
  [
    {
      fetchingData: true,
      brokenCredentials: true,
      attempt: { error_code: "3030", status: "no_data" },
      canceled: true,
      attemptDeleted: true,
      isRetry: true,
    },
    INTENTION_RUNNING,
  ],
  [
    {
      fetchingData: false,
      brokenCredentials: true,
      attempt: { error_code: "3030", status: "no_data" },
      canceled: true,
      attemptDeleted: true,
      isRetry: true,
    },
    INTENTION_BROKEN,
  ],
  [
    {
      fetchingData: false,
      brokenCredentials: false,
      attempt: { error_code: "3030", status: "no_data" },
      canceled: true,
      attemptDeleted: true,
      isRetry: true,
    },
    ATTEMPT_EMPTY_DATA,
  ],
  [
    {
      fetchingData: false,
      brokenCredentials: false,
      attempt: null,
      canceled: true,
      attemptDeleted: true,
      isRetry: true,
    },
    INTENTION_CANCELED,
  ],
  [
    {
      fetchingData: false,
      brokenCredentials: false,
      attempt: null,
      canceled: false,
      attemptDeleted: true,
      isRetry: true,
    },
    INTENTION_DELETED,
  ],
  [
    {
      fetchingData: false,
      brokenCredentials: false,
      attempt: null,
      canceled: false,
      attemptDeleted: false,
      isRetry: true,
    },
    INTENTION_QUEUED,
  ],
  [
    {
      fetchingData: false,
      brokenCredentials: false,
      attempt: null,
      canceled: false,
      attemptDeleted: false,
      isRetry: false,
    },
    INTENTION_WAITING,
  ],
];

describe("test Fetch Intention states without credentials", () => {
  test.each(cases_without_credentials)(
    "does output from %p match %p",
    (intention, state) => {
      let output = intentionState(intention);
      expect(output).toBe(state);
    },
  );
});

const cases_with_credentials = [
  [
    {
      fetchingData: true,
      brokenCredentials: true,
      attempt: { error_code: "3030", status: "no_data" },
      canceled: true,
      attemptDeleted: true,
      isRetry: true,
    },
    null,
    INTENTION_RUNNING,
  ],
];

describe("test Fetch Intention states with credentials", () => {
  test.each(cases_with_credentials)(
    "does output from %p-%p match %p",
    (intention, credentials, state) => {
      let output = intentionState(intention, credentials);
      expect(output).toBe(state);
    },
  );
});
