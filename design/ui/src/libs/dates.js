import addMonths from "date-fns/addMonths";
import addYears from "date-fns/addYears";
import endOfDay from "date-fns/endOfDay";
import endOfMonth from "date-fns/endOfMonth";
import format from "date-fns/format";
import getMonth from "date-fns/getMonth";
import getYear from "date-fns/getYear";
import isValid from "date-fns/isValid";
import lastDayOfYear from "date-fns/lastDayOfYear";
import parseISO from "date-fns/parseISO";
import startOfMonth from "date-fns/startOfMonth";
import startOfYear from "date-fns/startOfYear";
import isEqual from "lodash/isEqual";

function isoDateFormat(date) {
  return format(date, "yyyy-MM-dd");
}

function ymDateFormat(date) {
  return format(date, "yyyy-MM");
}

function ymDateParse(ymdate, isEndOfMonth = false) {
  let out = parseISO(ymdate, "yyyy-MM", Date());
  return isEndOfMonth ? endOfMonth(out) : out;
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
    "yyyy-MM-dd",
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

function smartDateParse(date, isEndOfMonth = false) {
  if (typeof date === "string") {
    return date.length === 7 ? ymDateParse(date, isEndOfMonth) : parseISO(date);
  }
  return date;
}

function anyDateToYm(date) {
  return ymDateFormat(smartDateParse(date));
}

function smartMonthRange({ start, end }) {
  if (!!start && !!end) {
    start = startOfMonth(smartDateParse(start));
    end = smartDateParse(end, true);
    if (
      start.getMonth() === 0 &&
      isEqual(endOfDay(lastDayOfYear(end)), endOfDay(end))
    ) {
      if (getYear(start) === getYear(end)) {
        return `${getYear(start)}`;
      } else {
        return `${getYear(start)} - ${getYear(end)}`;
      }
    }
    let ymStart = ymDateFormat(start);
    let ymEnd = ymDateFormat(end);
    if (ymStart === ymEnd) {
      return ymStart;
    }
    return `${ymStart} - ${ymEnd}`;
  } else if (!!start) {
    start = startOfMonth(smartDateParse(start));
    return `> ${ymDateFormat(start)}`;
  } else {
    end = smartDateParse(end, true);
    return `< ${ymDateFormat(end)}`;
  }
}

function lastFinishedMonthDate() {
  // the last month which is already over and therefore SUSHI data can be
  // harvested for it
  let out = addMonths(new Date(), -1);
  // setDate() does a in-place mutation and returns a timestamp as a number
  // so we call it separately and return the date object
  out.setDate(1);
  return out;
}

function lastFinishedMonth() {
  // the last month which is already over and therefore SUSHI data can be
  // harvested for it
  return ymDateFormat(lastFinishedMonthDate());
}

function lastCoveredMonth() {
  return ymDateFormat(lastCoveredMonthDate());
}

function lastCoveredMonthDate() {
  // the month before the last one - for that month SUSHI data can be
  // expected to already be available and thus it makes sense to use it
  // in computations and coverage reports
  return startOfMonth(addMonths(new Date(), -2));
}

function lastCoveredYearDate() {
  // the last whole year for which we can expect to have SUSHI data
  let lcm = lastCoveredMonthDate();
  if (lcm.getMonth() < 11)
    // if the last covered month is not December, we need to go back to the
    // previous year
    lcm = addYears(lcm, -1);
  return startOfYear(lcm);
}

function counterGuaranteedPeriodStartDate() {
  // the start date for the COUNTER guaranteed period where data should
  // be available for all months
  return startOfYear(addYears(new Date(), -2));
}

function counterGuaranteedPeriodStart() {
  return ymDateFormat(counterGuaranteedPeriodStartDate());
}

function getMonthAbbreviation(monthNumber, locale = "en") {
  const date = new Date(2020, monthNumber, 1);
  return date.toLocaleString(locale, { month: "short" });
}

export {
  anyDateToYm,
  counterGuaranteedPeriodStart,
  counterGuaranteedPeriodStartDate,
  getMonthAbbreviation,
  isoDateFormat,
  isoDateTimeFormat,
  isoDateTimeFormatSpans,
  lastCoveredMonth,
  lastCoveredMonthDate,
  lastCoveredYearDate,
  lastFinishedMonth,
  lastFinishedMonthDate,
  monthFirstDay,
  monthLastDay,
  monthsBetween,
  parseDateTime,
  smartDateParse,
  smartMonthRange,
  ymDateFormat,
  ymDateParse,
  ymFirstDay,
  ymLastDay,
};
