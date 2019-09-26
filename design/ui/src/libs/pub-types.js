let pubTypeToIcon = {
    'B': 'fa-book',  // book
    'J': 'fa-copy',  // journal
    'U': 'fa-question',  // unknown
    'D': 'fa-database',  // database
    'O': 'fa-folder',  // other
    'R': 'fa-sticky-note',  // report
    'N': 'fa-newspaper',  // newspaper
    'M': 'fa-compact-disk',  // multimedia
}

function iconForPubType(pubType) {
  if (pubType in pubTypeToIcon) {
    return pubTypeToIcon[pubType]
  }
  return pubTypeToIcon['U']
}

export {
  iconForPubType
}
