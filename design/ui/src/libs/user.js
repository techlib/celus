import { isoDateFormat, isoDateTimeFormat, parseDateTime } from "@/libs/dates";

function userToString(user, empty_str, skip_comma) {
  empty_str ??= "-";
  skip_comma = !!skip_comma;
  if (!user) {
    return empty_str;
  }
  if (user.last_name) {
    if (user.first_name) {
      if (skip_comma) {
        return `${user.first_name} ${user.last_name}`;
      } else {
        return `${user.first_name} ${user.last_name}`;
      }
    }
    return user.last_name;
  }
  if (user.email) {
    return user.email;
  }
  if (user.username) {
    return user.username;
  }
  if (user.pk) {
    return user.pk.toString();
  }
  return empty_str;
}

function dateAndUser(date, user, full_date) {
  full_date ??= false;
  if (typeof date === "string") {
    date = parseDateTime(date);
  }
  let date_part = "";
  if (full_date) {
    date_part = isoDateTimeFormat(date);
  } else {
    date_part = isoDateFormat(date);
  }
  if (!!user) {
    return `${date_part}, ${userToString(user, "", true)}`;
  } else {
    return date_part;
  }
}

export { dateAndUser, userToString };
