/*
    The interest_remap specifies not only how interest coming from the API should be
    mapped to the interest in the UI, but also which values are actually supported by
    the UI.
    This means that only those values in interest_remap.values are handled by the UI.
 */

let interest_remap = {
  'search': 'database',
  'full_text': 'title',
  'other': 'other',
  'denial': 'denial',
}

function createEmptyInterestRecord () {
  let out = {}
  for (let value of Object.values(interest_remap)) {
    out[value] = null
  }
  return out
}

function createLoadingInterestRecord () {
  let out = createEmptyInterestRecord()
  out['loading'] = true
  return out
}

function remapInterestRecord(input) {
  let out = {}
  for (let [key, value] of Object.entries(input)) {
    if (key in interest_remap) {
      out[interest_remap[key]] = value
    } else {
      // we do not allow unmapped interest keys
      // out[key] = value
    }
  }
  return out
}


export {
  createEmptyInterestRecord,
  createLoadingInterestRecord,
  remapInterestRecord,
}
