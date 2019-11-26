function userToString (user) {
  if (!user) {
    return '-'
  }
  if (user.last_name) {
    if (user.first_name) {
      return `${user.last_name}, ${user.first_name}`
    }
    return user.last_name
  }
  if (user.email) {
    return user.email
  }
  if (user.username) {
    return user.username
  }
  if (user.pk) {
    return user.pk.toString()
  }
  return '-'
}

export {
  userToString
}
