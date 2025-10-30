**Notification type:** {{ notification.get_type_display }}<br>
{% if notification.sushi_service %}**COUNTER version:** {{ notification.sushi_service.get_counter_release_display }}{% endif %}<br>
{% if notification.start_date or notification.end_date %}**Affected dates:** {% if notification.start_date and notification.end_date %}{{ notification.start_date|date:"Y-m-d" }} &ndash; {{ notification.end_date|date:"Y-m-d" }}{% elif notification.start_date %}since {{ notification.start_date|date:"Y-m-d" }}{% elif notification.end_date %}until {{ notification.end_date|date:"Y-m-d" }}{% endif %}{% endif %}<br>
{% if reports %}**Affected reports:** {{ reports }}{% endif %}

---

{{ notification.message }}

---

**Note**: This event was created automatically from a [COUNTER Registry](https://registry.countermetrics.org) notification. See the [list of notifications](https://registry.countermetrics.org/notifications).
