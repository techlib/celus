let pubTypes = [
  {code: 'B', icon: 'fa-book', title: 'pub_type.book'},
  {code: 'J', icon: 'fa-copy', title: 'pub_type.journal'},
  {code: 'D', icon: 'fa-database', title: 'pub_type.database'},
  {code: 'R', icon: 'fa-sticky-note', title: 'pub_type.report'},
  {code: 'N', icon: 'fa-newspaper', title: 'pub_type.newspaper'},
  {code: 'M', icon: 'fas fa-compact-disc', title: 'pub_type.multimedia'},
  {code: 'U', icon: 'fa-question', title: 'pub_type.unknown'},
  {code: 'O', icon: 'fa-folder', title: 'pub_type.other'},
]

let pubTypeToIcon = {}
for (let item of pubTypes) {
  pubTypeToIcon[item.code] = item.icon
}

function iconForPubType(pubType) {
  if (pubType in pubTypeToIcon) {
    return pubTypeToIcon[pubType]
  }
  return pubTypeToIcon['U']
}

export {
  pubTypes,
  pubTypeToIcon,
  iconForPubType,
}
