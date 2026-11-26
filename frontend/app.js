"use strict";
// Landing page behaviour: warm-up call, POST /ask (PRD FR-23), safe rendering of the answer.
(function () {
  var base = (window.DISHAA_CONFIG && window.DISHAA_CONFIG.API_BASE) || "";
  var form = document.getElementById("ask-form");
  var input = document.getElementById("query");
  var box = document.getElementById("answer");
  var text = document.getElementById("answer-text");
  var cites = document.getElementById("citations");
  var hero = document.getElementById("hero");

  // Respect reduced motion: jump the plane and trail to their final frame.
  if (hero && window.matchMedia("(prefers-reduced-motion: reduce)").matches && hero.pauseAnimations) {
    hero.pauseAnimations();
    hero.setCurrentTime(100);
  }

  // Wake the database while the visitor reads the page (Aurora auto-pause, ADR-026). Failure is silent.
  if (base) {
    fetch(base + "/health", { method: "GET" }).catch(function () {});
  }

  document.getElementById("start").addEventListener("click", function () {
    setTimeout(function () { input.focus(); }, 0);
  });

  // Speech to text through the browser's own feature, where it exists. No audio leaves the browser path we control.
  var mic = document.getElementById("mic");
  var Rec = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Rec) {
    mic.disabled = true;
    mic.title = "Voice input is not supported in this browser";
  } else {
    mic.addEventListener("click", function () {
      var r = new Rec();
      r.lang = "en-US";
      r.onresult = function (e) { input.value = e.results[0][0].transcript; input.focus(); };
      r.start();
    });
  }

  function show(message, citations) {
    text.textContent = message;
    cites.textContent = "";
    (citations || []).forEach(function (c) {
      var li = document.createElement("li");
      var label = (c.title || c.url || "source") + (c.last_verified ? " (last verified " + c.last_verified + ")" : "");
      if (c.url && /^https?:\/\//i.test(c.url)) {
        var a = document.createElement("a");
        a.href = c.url;
        a.target = "_blank";
        a.rel = "noopener noreferrer";
        a.textContent = label;
        li.appendChild(a);
      } else {
        li.textContent = label;
      }
      cites.appendChild(li);
    });
    box.hidden = false;
  }

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var message = input.value.trim();
    if (!message) return;
    if (!base) {
      show("The DISHAA API is not deployed yet, so there is nothing to answer this question. Set API_BASE in config.js.", []);
      return;
    }
    show("Thinking…", []);
    fetch(base + "/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: message, conversation: {} }),
    })
      .then(function (res) {
        if (!res.ok) throw new Error("status " + res.status);
        return res.json();
      })
      .then(function (data) { show(String(data.answer || ""), data.citations); })
      .catch(function () { show("Something went wrong. Please try again in a moment.", []); });
  });
})();
