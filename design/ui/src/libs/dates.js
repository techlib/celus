import format from 'date-fns/format'

function isoDateFormat (date) {
    return format(date, 'YYYY-MM-DD')
}

export {isoDateFormat}
