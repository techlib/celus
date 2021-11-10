import format from "date-fns/format";
import getYear from "date-fns/getYear";
import getMonth from "date-fns/getMonth";
import parseISO from "date-fns/parseISO";
import isValid from "date-fns/isValid";
import addMonths from "date-fns/addMonths";

function isoDateFormat(date) {
  return format(date, "yyyy-MM-dd");
}

function ymDateFormat(date) {
  return format(date, "yyyy-MM");
}

function ymDateParse(ymdate) {
  return parseISO(ymdate, "yyyy-MM", Date());
}

function ymFirstDay(ymdate) {
  return monthFirstDay(ymDateParse(ymdate));
}

function monthFirstDay(date) {
  return format(new Date(getYear(date), getMonth(date), 1), "yyyy-MM-dd");
}

function monthLastDay(date) {
  return format(new Date(getYear(date), getMonth(date) + 1, 0), "yyyy-MM-dd");
}

function ymLastDay(ymdate) {
  return monthLastDay(ymDateParse(ymdate));
}

function parseDateTime(text) {
  if (text === null) {
    return null;
  }
  const date = parseISO(text);
  if (isValid(date)) {
    return date;
  }
  return null;
}

function isoDateTimeFormat(date) {
  if (!date) {
    return "-";
  }
  if (typeof date === "string") {
    date = parseDateTime(date);
  }
  return format(date, "yyyy-MM-dd HH:mm:ss");
}

function isoDateTimeFormatSpans(date) {
  if (typeof date === "string") {
    date = parseDateTime(date);
  }
  return `<span class="date">${format(
    date,
    "yyyy-MM-dd"
  )}</span> <span class="time">${format(date, "HH:mm:ss")}</span>`;
}

function monthsBetween(start, end) {
  let startMonth = ymDateParse(start);
  const endMonth = ymDateParse(end);
  let months = [startMonth];
  while (startMonth < endMonth) {
    startMonth = addMonths(startMonth, 1);
    months.push(startMonth);
  }
  return months;
}

export {
  isoDateFormat,
  monthFirstDay,
  monthLastDay,
  ymDateFormat,
  ymDateParse,
  ymFirstDay,
  ymLastDay,
  parseDateTime,
  isoDateTimeFormat,
  isoDateTimeFormatSpans,
  monthsBetween,
};
