/* Reminders shown on the site. The daily check (scheduled task "portfolio-reminders") edits this file.
   war.trigger: date (YYYY-MM-DD) the escalation was detected, or null. war.due = trigger + 3 days.
   jan.due: fallback buy date if no escalation happened before it. notified: the reminder was already sent. */
window.REMINDERS = {
  war: {
    trigger: null,
    due: null,
    notified: false,
    rule: "נחשב: חידוש הלחימה בקנה מידה מלא (קריסת הפסקת האש מיוני, או מערכת תקיפות אמריקאית מתמשכת בשטח איראן). תקיפות הגנתיות נקודתיות לא נחשבות."
  },
  jan: {
    due: "2027-01-01",
    notified: false
  }
};
