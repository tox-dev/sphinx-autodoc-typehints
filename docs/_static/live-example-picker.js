// Show every live example on the page as rendered with the options picked in the conf.py tab of any of them.
"use strict";

(() => {
  const about = document.getElementById("live-example-picker");
  if (!about) {
    return;
  }
  const { options, conf, data: dataUrl } = JSON.parse(about.textContent);
  const forms = [...document.querySelectorAll("form.live-example-picker")];
  const outputs = [...document.querySelectorAll(".live-example-output[data-live-example]")].map((output) => ({
    output,
    at: Number(output.dataset.liveExample),
    body: output.innerHTML,
  }));
  const dependency = options.map((option) => options.findIndex((other) => other.name === option.dependsOn));
  const storageKey = "sphinx-autodoc-typehints.live-example-picker";
  const defaults = options.map(() => 0);
  let loading;

  // an option needing another one that is switched off changes nothing, so it keeps its default
  const active = (picked, at) => dependency[at] < 0 || Boolean(options[dependency[at]].values[picked[dependency[at]]]);
  const canonical = (picked) => picked.map((value, at) => (active(picked, at) ? value : 0));
  const read = (form) =>
    options.map((option) => {
      const field = form.elements.namedItem(option.name);
      return field.type === "checkbox" ? option.values.indexOf(field.checked) : Number(field.value);
    });
  const confText = (picked) => conf + picked.map((value, at) => (value ? options[at].lines[value] : "")).join("");

  const showControls = (picked) => {
    const text = confText(picked);
    forms.forEach((form) => {
      options.forEach((option, at) => {
        const field = form.elements.namedItem(option.name);
        if (field.type === "checkbox") {
          field.checked = option.values[picked[at]] === true;
          field.disabled = !active(picked, at);
        } else {
          field.value = String(picked[at]);
          field.forEach((radio) => {
            radio.disabled = !active(picked, at);
          });
        }
      });
      form.querySelector("pre").innerHTML = text;
    });
  };
  const load = () => {
    loading ??= new Promise((resolve, reject) => {
      window.liveExamplePicker = { receive: resolve };
      const script = document.createElement("script");
      script.src = dataUrl;
      script.onerror = reject;
      document.head.append(script);
    });
    return loading;
  };
  const showExamples = async (picked, status) => {
    if (picked.every((value) => value === 0)) {
      outputs.forEach(({ output, body }) => {
        output.innerHTML = body;
      });
      return;
    }
    if (status) {
      status.textContent = "Loading the examples for these options";
    }
    let variants;
    try {
      variants = await load();
    } catch {
      if (status) {
        status.textContent = "The examples for these options failed to load";
      }
      return;
    }
    if (status) {
      status.textContent = "";
    }
    if (canonical(read(forms[0])).join("") !== picked.join("")) {
      return; // the reader picked again while the variants loaded
    }
    outputs.forEach(({ output, at }) => {
      const relevant = new Set(variants.relevant[at]);
      const key = canonical(picked.map((value, index) => (relevant.has(index) ? value : 0))).join("");
      output.innerHTML = variants.bodies[variants.examples[at][key]];
    });
  };
  const save = (picked) => {
    try {
      localStorage.setItem(storageKey, JSON.stringify(Object.fromEntries(options.map((o, at) => [o.name, picked[at]]))));
    } catch {
      // without storage the choice lasts until the page closes
    }
  };
  const restore = () => {
    try {
      const saved = JSON.parse(localStorage.getItem(storageKey) ?? "{}") ?? {};
      return options.map((option) => {
        const value = saved[option.name];
        return Number.isInteger(value) && value >= 0 && value < option.values.length ? value : 0;
      });
    } catch {
      return defaults;
    }
  };
  const pick = (picked, status) => {
    const chosen = canonical(picked);
    showControls(chosen);
    save(chosen);
    showExamples(chosen, status);
  };

  forms.forEach((form) => {
    const status = form.querySelector(".lep-status");
    form.addEventListener("change", () => pick(read(form), status));
    form.addEventListener("reset", (event) => {
      event.preventDefault();
      pick(defaults, status);
    });
  });
  // a tooltip opens on hover and focus through the stylesheet, on a tap through this, and Escape closes it
  document.querySelectorAll(".lep-tipwrap").forEach((wrap) => {
    const button = wrap.querySelector(".lep-info");
    button.addEventListener("click", () => {
      wrap.classList.remove("lep-dismissed");
      wrap.classList.toggle("lep-open");
    });
    wrap.addEventListener("pointerleave", () => wrap.classList.remove("lep-dismissed", "lep-open"));
    button.addEventListener("blur", () => wrap.classList.remove("lep-dismissed", "lep-open"));
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      document.querySelectorAll(".lep-tipwrap").forEach((wrap) => {
        wrap.classList.remove("lep-open");
        wrap.classList.add("lep-dismissed");
      });
    }
  });

  const saved = canonical(restore());
  showControls(saved);
  showExamples(saved, null);
})();
