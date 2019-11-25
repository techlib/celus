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
    return format(date, 'YYYY-MM-DD HH:mm:ss')
}

function isoDateTimeFormatSpans (date) {
    return `<span class="date">${format(date, 'YYYY-MM-DD')}</span> <span class="time">${format(date, 'HH:mm:ss')}</span>`
}

export {
  isoDateFormat,
  ymDateFormat,
  parseDateTime,
  isoDateTimeFormat,
  isoDateTimeFormatSpans,
}
