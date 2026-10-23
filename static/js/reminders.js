(function () {
  "use strict";

  var POLL_MS = 30000;
  var DUE_WINDOW_MINUTES = 10;
  var SNOOZE_MINUTES = 5;
  var FIRED_KEY = "smartmeds.firedReminders";
  var SNOOZED_KEY = "smartmeds.snoozedReminders";

  var script = document.currentScript;
  var endpoint =
    (script && script.getAttribute("data-reminders-url")) ||
    "/prescriptions/reminders/";

  var banner = document.getElementById("medicine-reminder");
  var bannerText = banner ? banner.querySelector("[data-reminder-text]") : null;
  var enableButton = document.querySelector("[data-enable-reminders]");
  var stopButton = banner ? banner.querySelector("[data-reminder-stop]") : null;
  var snoozeButton = banner ? banner.querySelector("[data-reminder-snooze]") : null;

  var schedule = [];
  var timezone = null;
  var active = null;
  var audioContext = null;
  var alarmTimer = null;
  var lastNotification = null;
  var polling = false;

  function readStore(key) {
    try {
      var raw = window.localStorage.getItem(key);
      var data = raw ? JSON.parse(raw) : {};
      return data && typeof data === "object" ? data : {};
    } catch (error) {
      return {};
    }
  }

  function writeStore(key, value) {
    try {
      window.localStorage.setItem(key, JSON.stringify(value));
    } catch (error) {
      /* Storage can be unavailable in private browsing. */
    }
  }

  var fired = readStore(FIRED_KEY);
  var snoozed = readStore(SNOOZED_KEY);

  function pruneStore(store, dateKey) {
    var changed = false;
    Object.keys(store).forEach(function (key) {
      if (key.indexOf(dateKey + "|") !== 0) {
        delete store[key];
        changed = true;
      }
    });
    return changed;
  }

  function browserTimezone() {
    try {
      return Intl.DateTimeFormat().resolvedOptions().timeZone || null;
    } catch (error) {
      return null;
    }
  }

  function currentClock(zone) {
    var now = new Date();
    var parts;
    try {
      parts = new Intl.DateTimeFormat("en-GB", {
        timeZone: zone || browserTimezone() || undefined,
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        hourCycle: "h23"
      }).formatToParts(now);
    } catch (error) {
      parts = new Intl.DateTimeFormat("en-GB", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        hourCycle: "h23"
      }).formatToParts(now);
    }

    var values = {};
    parts.forEach(function (part) {
      if (part.type !== "literal") {
        values[part.type] = part.value;
      }
    });

    var hour = parseInt(values.hour, 10);
    var minute = parseInt(values.minute, 10);
    if (!Number.isFinite(hour) || !Number.isFinite(minute)) {
      return null;
    }
    hour = hour % 24;

    return {
      date: values.year + "-" + values.month + "-" + values.day,
      minutes: hour * 60 + minute,
      label: values.hour + ":" + values.minute
    };
  }

  function parseTime(value) {
    var match = /^(\d{1,2}):(\d{2})$/.exec(String(value || ""));
    if (!match) {
      return null;
    }
    var hour = parseInt(match[1], 10);
    var minute = parseInt(match[2], 10);
    if (hour > 23 || minute > 59) {
      return null;
    }
    return hour * 60 + minute;
  }

  function getAudioContext() {
    var AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass) {
      return null;
    }
    if (!audioContext) {
      try {
        audioContext = new AudioContextClass();
      } catch (error) {
        return null;
      }
    }
    return audioContext;
  }

  function unlockAudio() {
    var context = getAudioContext();
    if (context && context.state === "suspended") {
      context.resume().catch(function () {});
    }
  }

  function beep(context, frequency, start, duration, volume) {
    var oscillator = context.createOscillator();
    var gain = context.createGain();
    oscillator.type = "sine";
    oscillator.frequency.setValueAtTime(frequency, start);
    gain.gain.setValueAtTime(0.0001, start);
    gain.gain.exponentialRampToValueAtTime(volume, start + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, start + duration);
    oscillator.connect(gain);
    gain.connect(context.destination);
    oscillator.start(start);
    oscillator.stop(start + duration + 0.02);
  }

  function playAlarmPattern() {
    var context = getAudioContext();
    if (!context) {
      return;
    }
    if (context.state === "suspended") {
      context.resume().catch(function () {});
    }
    var start = context.currentTime;
    [0, 0.32, 0.64].forEach(function (offset) {
      beep(context, 880, start + offset, 0.18, 0.22);
    });
    [1.15, 1.47].forEach(function (offset) {
      beep(context, 660, start + offset, 0.2, 0.2);
    });
  }

  function playConfirmationTone() {
    var context = getAudioContext();
    if (!context) {
      return;
    }
    if (context.state === "suspended") {
      context.resume().catch(function () {});
    }
    var start = context.currentTime;
    beep(context, 880, start, 0.12, 0.16);
    beep(context, 1174, start + 0.16, 0.16, 0.16);
  }

  function startAlarm() {
    stopAlarm();
    if (!getAudioContext()) {
      return;
    }
    playAlarmPattern();
    alarmTimer = window.setInterval(playAlarmPattern, 5000);
  }

  function stopAlarm() {
    if (alarmTimer) {
      window.clearInterval(alarmTimer);
      alarmTimer = null;
    }
  }

  function showBanner(items) {
    if (!banner || !bannerText) {
      return;
    }
    var description = items
      .map(function (item) {
        var dosage = item.dosage ? " (" + item.dosage + ")" : "";
        return item.name + dosage + " at " + item.time;
      })
      .join(", ");
    bannerText.textContent = "It's time to take " + description + ".";
    banner.hidden = false;
  }

  function hideBanner() {
    if (banner) {
      banner.hidden = true;
    }
  }

  function notify(items) {
    if (!("Notification" in window) || Notification.permission !== "granted") {
      return;
    }
    var body = items
      .map(function (item) {
        return item.name + " at " + item.time;
      })
      .join(", ");
    try {
      lastNotification = new Notification("Medicine reminder", {
        body: "It's time to take " + body + ".",
        tag: "smartmeds-medicine-reminder",
        requireInteraction: true
      });
      lastNotification.onclick = function () {
        window.focus();
        this.close();
      };
    } catch (error) {
      lastNotification = null;
    }
  }

  function trigger(items, keys) {
    active = { items: items, keys: keys };
    showBanner(items);
    startAlarm();
    notify(items);
    if (navigator.vibrate) {
      try {
        navigator.vibrate([300, 150, 300, 150, 500]);
      } catch (error) {
        /* Vibration is optional. */
      }
    }
  }

  function checkDue() {
    if (!schedule.length) {
      return;
    }
    var clock = currentClock(timezone);
    if (!clock) {
      return;
    }

    var storeChanged = pruneStore(fired, clock.date);
    storeChanged = pruneStore(snoozed, clock.date) || storeChanged;

    var dueItems = [];
    var dueKeys = [];
    var now = Date.now();

    schedule.forEach(function (medicine) {
      var key = clock.date + "|" + medicine.id + "|" + medicine.time;
      var snoozeUntil = snoozed[key];
      var forceDue = false;
      if (snoozeUntil) {
        if (now >= snoozeUntil) {
          delete snoozed[key];
          delete fired[key];
          storeChanged = true;
          forceDue = true;
        } else {
          return;
        }
      }

      if (!forceDue) {
        if (fired[key]) {
          return;
        }

        var dueMinutes = parseTime(medicine.time);
        if (dueMinutes === null) {
          return;
        }
        if (
          clock.minutes < dueMinutes ||
          clock.minutes - dueMinutes > DUE_WINDOW_MINUTES
        ) {
          return;
        }
      }

      fired[key] = now;
      storeChanged = true;
      dueItems.push(medicine);
      dueKeys.push(key);
    });

    if (storeChanged) {
      writeStore(FIRED_KEY, fired);
      writeStore(SNOOZED_KEY, snoozed);
    }

    if (dueItems.length) {
      trigger(dueItems, dueKeys);
    }
  }

  function fetchReminders() {
    if (polling || !endpoint) {
      return;
    }
    polling = true;
    window
      .fetch(endpoint, {
        credentials: "same-origin",
        headers: { Accept: "application/json" }
      })
      .then(function (response) {
        if (!response.ok) {
          throw new Error("Reminder request failed");
        }
        return response.json();
      })
      .then(function (data) {
        schedule = Array.isArray(data.medicines) ? data.medicines : [];
        timezone = data.timezone || browserTimezone();
        checkDue();
      })
      .catch(function () {
        /* A failed poll is retried on the next tick. */
      })
      .then(function () {
        polling = false;
      });
  }

  function tick() {
    fetchReminders();
    checkDue();
  }

  function refreshEnableButton() {
    if (!enableButton) {
      return;
    }
    if (!("Notification" in window)) {
      enableButton.hidden = true;
      return;
    }
    if (Notification.permission === "granted") {
      enableButton.hidden = true;
      return;
    }
    enableButton.hidden = false;
    if (Notification.permission === "denied") {
      enableButton.textContent = "Alerts blocked in browser settings";
      enableButton.disabled = true;
      return;
    }
    enableButton.textContent = "Enable medicine alerts";
    enableButton.disabled = false;
  }

  if (enableButton) {
    refreshEnableButton();
    enableButton.addEventListener("click", function () {
      unlockAudio();
      if (!("Notification" in window) || Notification.permission === "denied") {
        refreshEnableButton();
        return;
      }
      var settled = false;
      function handlePermission(permission) {
        if (settled) {
          return;
        }
        settled = true;
        if (permission === "granted") {
          playConfirmationTone();
        }
        refreshEnableButton();
      }

      try {
        var request = Notification.requestPermission(handlePermission);
        if (request && typeof request.then === "function") {
          request.then(handlePermission).catch(function () {
            refreshEnableButton();
          });
        }
      } catch (error) {
        refreshEnableButton();
      }
    });
  }

  if (stopButton) {
    stopButton.addEventListener("click", function () {
      stopAlarm();
      hideBanner();
      if (lastNotification) {
        lastNotification.close();
        lastNotification = null;
      }
      active = null;
    });
  }

  if (snoozeButton) {
    snoozeButton.addEventListener("click", function () {
      if (active) {
        var snoozeUntil = Date.now() + SNOOZE_MINUTES * 60000;
        active.keys.forEach(function (key) {
          snoozed[key] = snoozeUntil;
          fired[key] = Date.now();
        });
        writeStore(SNOOZED_KEY, snoozed);
        writeStore(FIRED_KEY, fired);
      }
      stopAlarm();
      hideBanner();
      if (lastNotification) {
        lastNotification.close();
        lastNotification = null;
      }
      active = null;
    });
  }

  ["pointerdown", "keydown"].forEach(function (eventName) {
    document.addEventListener(eventName, unlockAudio, { once: true, passive: true });
  });

  document.addEventListener("visibilitychange", function () {
    if (!document.hidden) {
      tick();
    }
  });

  window.setInterval(tick, POLL_MS);
  tick();
})();
