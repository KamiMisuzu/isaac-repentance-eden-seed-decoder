const HELP_CODE = {
  "rev.prefix": "enumerate all labels with this prefix\ne.g. T44 → T440 · T441 · T44A …\nignores start/end when set",
  "rev.start": "start_u32 — decimal or 0x hex",
  "rev.end": "end_u32 — default 0xffffffff",
  "rev.red": "red_hud = red1232 / 2\nmatch: |red_hud − input| ≤ 0.01",
  "rev.soul": "soul_hud = soul1235 / 2\nmatch: |soul_hud − input| ≤ 0.01",
  "stat.damage": "Δ = u01×2 − 1  (7BBBD0)\nmatch: |Δ − input| ≤ 0.006",
  "stat.speed": "Δ = u01×2 − 1\nmatch: |Δ − input| ≤ 0.006",
  "stat.tears": "Δ = u01×1.5 − 0.75\nmatch: |Δ − input| ≤ 0.006",
  "stat.range":
    "rng_delta = u01(v38) × 120 − 60\nrange1312 = 260 + rng_delta\ndisplay   = range1312 / 40\n          = 6.5 + rng_delta / 40\nmatch: |display − input| ≤ 0.006",
  "stat.shotSpeed": "Δ = u01×0.5 − 0.25\nmatch: |Δ − input| ≤ 0.006",
  "stat.luck": "Δ = u01×2 − 1\nmatch: |Δ − input| ≤ 0.006",
  "pocket.trinketId": "trinket collectible id\nneeds trinket_pool.json",
  "pocket.cardId": "card_id on HUD card slot",
  "pocket.pillId": "pill_effect on HUD pill slot",
  "rev.passive": "collectible1 · passive slot (v161)\nneeds proc.json",
  "rev.active": "collectible2 · active slot (v162)\nneeds proc.json",
};

let openHelpPop = null;
let openHelpBtn = null;

function closeFieldHelp() {
  if (openHelpPop) openHelpPop.classList.add("hidden");
  if (openHelpBtn) openHelpBtn.setAttribute("aria-expanded", "false");
  openHelpPop = null;
  openHelpBtn = null;
}

function initFieldHelp() {
  document.querySelectorAll(".help-btn[data-help]").forEach((btn) => {
    const key = btn.dataset.help;
    btn.setAttribute("aria-controls", `help-${key}`);
    const pop = document.querySelector(`[data-help-pop="${key}"]`);
    if (pop && !pop.id) pop.id = `help-${key}`;

    btn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      const key = btn.dataset.help;
      const pop = document.querySelector(`[data-help-pop="${key}"]`);
      if (!pop) return;
      const willOpen = pop.classList.contains("hidden");
      closeFieldHelp();
      if (willOpen) {
        pop.classList.remove("hidden");
        btn.setAttribute("aria-expanded", "true");
        openHelpPop = pop;
        openHelpBtn = btn;
      }
    });
  });

  document.addEventListener("click", (e) => {
    if (!openHelpPop) return;
    if (openHelpPop.contains(e.target) || e.target === openHelpBtn) return;
    closeFieldHelp();
  });

  refreshHelpCodes();
}

function refreshHelpCodes() {
  document.querySelectorAll("pre[data-help-code]").forEach((pre) => {
    const code = HELP_CODE[pre.dataset.helpCode];
    if (code) {
      pre.textContent = code;
      pre.classList.remove("hidden");
    } else {
      pre.textContent = "";
      pre.classList.add("hidden");
    }
  });
  document.querySelectorAll(".help-btn[data-help]").forEach((btn) => {
    btn.setAttribute("aria-label", typeof t === "function" ? t("help.btn") : "?");
  });
}

document.addEventListener("DOMContentLoaded", initFieldHelp);
