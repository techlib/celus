let pubTypes = [
  {code: 'B', icon: 'fa-book', title: 'pub_type.book'},
  {code: 'J', icon: 'fa-copy', title: 'pub_type.journal'},
  {code: 'D', icon: 'fa-database', title: 'pub_type.database'},
  {code: 'R', icon: 'fa-sticky-note', title: 'pub_type.report'},
  {code: 'N', icon: 'fa-newspaper', title: 'pub_type.newspaper'},
  {code: 'M', icon: 'fas fa-compact-disc', title: 'pub_type.multimedia'},
  {code: 'U', icon: 'fa-question', title: 'pub_type.unknown'},
  {code: 'O', icon: 'fa-folder', title: 'pub_type.other'},
  {code: 'A', icon: 'fa-clipboard', title: 'pub_type.article'},
  {code: 'S', icon: 'fa-book-open', title: 'pub_type.book_segment'},
  {code: 'T', icon: 'fa-table', title: 'pub_type.dataset'},
  {code: 'P', icon: 'fa-building', title: 'pub_type.platform'},
  {code: 'I', icon: 'fa-bars', title: 'pub_type.repository_item'},
  {code: 'H', icon: 'fas fa-scroll', title: 'pub_type.thesis_or_dissertation'},


]

let pubTypeToIcon = {}
for (let item of pubTypes) {
  pubTypeToIcon[item.code] = item.icon
}

let codeToPubType = {}
for (let item of pubTypes) {
  codeToPubType[item.code] = item
}


function iconForPubType(pubType) {
  if (pubType in pubTypeToIcon) {
    return pubTypeToIcon[pubType]
  }
  return pubTypeToIcon['U']
}

function titleForPubType(pubType) {
  if (pubType in codeToPubType) {
    return codeToPubType[pubType].title
  }
  return codeToPubType['U'].title
}

export {
  pubTypes,
  pubTypeToIcon,
  iconForPubType,
  titleForPubType,
}
