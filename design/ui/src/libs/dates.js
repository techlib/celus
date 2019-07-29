import format from 'date-fns/format'

function isoDateFormat (date) {
    return format(date, 'YYYY-MM-DD')
}

function ymDateFormat (date) {
    return format(date, 'YYYY-MM')
}

export {
  isoDateFormat,
  ymDateFormat,
}
