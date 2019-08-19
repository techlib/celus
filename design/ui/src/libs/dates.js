import format from 'date-fns/format'
import parse from 'date-fns/parse'

function isoDateFormat (date) {
    return format(date, 'YYYY-MM-DD')
}

function ymDateFormat (date) {
    return format(date, 'YYYY-MM')
}

function parseDateTime (text) {
    return parse(text)
}

function isoDateTimeFormat (date) {
    return format(date, 'YYYY-MM-DD hh:mm:ss')
}

export {
  isoDateFormat,
  ymDateFormat,
  parseDateTime,
  isoDateTimeFormat,
}
