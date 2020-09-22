function createEmptyInterestRecord() {
  return {};
}

function createLoadingInterestRecord() {
  let out = createEmptyInterestRecord();
  out["loading"] = true;
  return out;
}

export { createEmptyInterestRecord, createLoadingInterestRecord };
