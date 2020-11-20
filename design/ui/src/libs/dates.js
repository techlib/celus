import format from "date-fns/format";
import getYear from "date-fns/getYear";
import getMonth from "date-fns/getMonth";
import parseISO from "date-fns/parseISO";
import isValid from "date-fns/isValid";

function isoDateFormat(date) {
  return format(date, "yyyy-MM-dd");
}

function ymDateFormat(date) {
  return format(date, "yyyy-MM");
}

function ymFirstDay(ymdate) {
  let parsed = parseISO(ymdate, "yyyy-MM", Date());
  return format(new Date(getYear(parsed), getMonth(parsed), 1), "yyyy-MM-dd");
}

function ymLastDay(ymdate) {
  let parsed = parseISO(ymdate, "yyyy-MM", Date());
  return format(
    new Date(getYear(parsed), getMonth(parsed) + 1, 0),
    "yyyy-MM-dd"
  );
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

export {
  isoDateFormat,
  ymDateFormat,
  ymFirstDay,
  ymLastDay,
  parseDateTime,
  isoDateTimeFormat,
  isoDateTimeFormatSpans,
};
