---
name: travel-aware-event-reminders
description: >
  Use when a calendar event has a physical address: add a day-before
  reminder around 9 AM and a leave-soon reminder based on drive time from
  home, then re-check the weather a few days before a long drive and move
  the leave-soon reminder earlier if conditions will slow the trip.
  Triggers: new event with a street address, drive-time reminder, weather
  check before a long drive. Skip video-call links, events near home, and
  declined or someone else's events.
---
# Travel-aware event reminders

This sets pop-up reminders on calendar events that have a real street address, and adjusts them for weather on long drives. The caller supplies the user's home address, time zone and which calendars to scan, usually from the vault and memory.

## Which events count
- Timed or all-day events with a physical street address in the location field or clearly in the description. Skip video links, "home", vague places with no address, and events the user isn't attending (declined, or someone else's shift or work calendar).
- Skip events the user's own home address or a place within about 10 minutes of it.
- Skip recurring social events the user already has reminders tuned for, unless the address changed. When unsure, leave existing custom reminders alone and mention it.

## 1. Set reminders when an event is first seen
1. Estimate drive time from home to the address, using a routing service (for example OSRM, or a maps lookup). Note the distance.
2. **Day-before reminder:** a pop-up at about 9:00 AM local time the day before. Minutes before start = minutes from that 9:00 AM to the event start. For all-day events, use 9:00 AM the day before the date.
3. **Leave-soon reminder** (only if drive time is about 15 minutes or more):
   - Departure = start time minus drive time minus about 10 minutes of arrival buffer. Round to a clean 5-minute mark.
   - Reminder fires 30 minutes before departure.
   - If the event is all-day but the details give an arrival time, convert the event to timed first only if the user asked for that; otherwise skip the leave-soon reminder and mention it.
4. Keep any reminders the user already set that differ from these, unless they're the old versions of these same two. Don't use more than 5 reminders total.
5. Don't change the title, time, location, guests or notes. Send no guest updates.
6. Watch for time zones. The appointment may be in another zone from home, so state both when it matters.

## 2. Weather check a few days before (drives over about 1 hour)
Roughly 2 days before the event:
1. Confirm the event still exists at the same time and place. If it moved or was canceled, adjust or stop, and report.
2. Check the forecast for the travel window along the route, covering origin, passes or high points, open stretches and the destination area. Look for snow, ice, wind, fog and heavy rain, plus state DOT advisories or closures. For a round trip the same day, check the return drive too.
3. Decide extra time:
   - Clear and dry needs nothing.
   - Light snow, wind or rain needs about 30–45 minutes.
   - A winter storm or icy roads needs an hour or more, or a suggestion to leave the day before or reschedule.
4. Move only the leave-soon reminder so it fires 30 minutes before the new departure. Leave everything else untouched.
5. Report to the user:
   - the forecast in a sentence or two
   - whether the reminder moved
   - the new reminder and departure times in their time zone
   - any safety advice

   Never contact the venue or anyone else.

## Report
For each event you touched, list:
- event, date and time
- distance and drive time
- the reminders now set
- anything skipped and why

Keep it short.
