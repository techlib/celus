import format from 'date-fns/format'
import parseISO from 'date-fns/parseISO'

function isoDateFormat (date) {
    return format(date, 'yyyy-MM-dd')
}

function ymDateFormat (date) {
    return format(date, 'yyyy-MM')
}

function parseDateTime (text) {
    return parseISO(text)
}

function isoDateTimeFormat (date) {
    return format(date, 'yyyy-MM-dd HH:mm:ss')
}

function isoDateTimeFormatSpans (date) {
    return `<span class="date">${format(date, 'yyyy-MM-dd')}</span> <span class="time">${format(date, 'HH:mm:ss')}</span>`
}

export {
  isoDateFormat,
  ymDateFormat,
  parseDateTime,
  isoDateTimeFormat,
  isoDateTimeFormatSpans,
}
