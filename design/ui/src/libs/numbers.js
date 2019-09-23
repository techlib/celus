import numeral from 'numeral'

function formatInteger(integer) {
  if (integer == null) {
    return '-'
  }
  return numeral(integer).format('0,0').replace(/,/g, ' ')
}

export {
  formatInteger
}
