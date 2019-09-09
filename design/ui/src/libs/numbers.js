import numeral from 'numeral'

function formatInteger(integer) {
  return numeral(integer).format('0,0').replace(/,/g, ' ')
}

export {
  formatInteger
}
