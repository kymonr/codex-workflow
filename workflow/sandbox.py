"""Isolated QuickJS sandbox for one workflow script.

QuickJS cannot convert a Python dict into a JS value, so host bridges use JSON
strings. The asynchronous job pump keeps every QuickJS operation on the calling
thread while agent work runs in bounded worker threads. No time limit is set,
because QuickJS forbids Python callables when one is active.
"""

from __future__ import annotations

import re
from typing import Any, Callable

from workflow.errors import SandboxError
from workflow.pump import DEFAULT_MAX_AGENTS, run_job_pump

_MAX_SCRIPT_CHARS = 256_000
_MEMORY_LIMIT_BYTES = 32 * 1024 * 1024
_EXPORT_CONST = re.compile(r"^export\s+const\s+", re.MULTILINE)
_OTHER_EXPORT = re.compile(r"^export\s+", re.MULTILINE)

PREAMBLE = r"""
(function () {
  function deny(name) {
    return function () {
      throw new Error(name + " is disabled in workflow sandbox");
    };
  }
  function DisabledDate() {
    throw new Error("Date is disabled in workflow sandbox");
  }
  DisabledDate.now = deny("Date.now");
  DisabledDate.parse = deny("Date.parse");
  DisabledDate.UTC = deny("Date.UTC");
  Object.freeze(DisabledDate);
  globalThis.Date = DisabledDate;

  Object.defineProperty(Math, "random", {
    value: deny("Math.random"),
    writable: false,
    configurable: false,
    enumerable: false
  });
  Object.freeze(Math);

  eval = deny("eval");
  Function = deny("Function");

  function notInPr2(name) {
    return function () {
      throw new Error(name + " is not available in PR2");
    };
  }
  globalThis.workflow = notInPr2("workflow()");
  globalThis.phase = notInPr2("phase()");
})();

var __pending = Object.create(null);

function __deliver(id, packedJson) {
  var rec = __pending[id];
  delete __pending[id];
  if (!rec) return;

  var packed;
  try {
    packed = JSON.parse(packedJson);
  } catch (e) {
    rec.reject(new Error("invalid agent completion envelope"));
    return;
  }
  if (!packed || typeof packed !== "object" || typeof packed.ok !== "boolean") {
    rec.reject(new Error("invalid agent completion envelope"));
    return;
  }
  if (!packed.ok) {
    rec.reject(new Error(String(packed.error || "agent failed")));
  } else {
    rec.resolve(packed.value);
  }
}

function agent(prompt, opts) {
  if (typeof prompt !== "string") {
    throw new Error("agent() prompt must be a string");
  }
  if (prompt.trim() === "") {
    throw new Error("agent() prompt must be non-empty");
  }
  if (opts === undefined || opts === null) {
    opts = {};
  } else if (typeof opts !== "object" || Array.isArray(opts)) {
    throw new Error("agent() opts must be an object");
  }

  return new Promise(function (resolve, reject) {
    try {
      var id = __agent_start(JSON.stringify({ prompt: prompt, opts: opts }));
      if (typeof id !== "string" || id === "") {
        reject(new Error("agent() host returned an invalid job id"));
        return;
      }
      __pending[id] = { resolve: resolve, reject: reject };
    } catch (e) {
      reject(e);
    }
  });
}

function parallel(thunks) {
  if (!Array.isArray(thunks)) {
    throw new Error("parallel() expects an array of functions");
  }
  if (thunks.length > 4096) {
    throw new Error("parallel() supports at most 4096 entries");
  }
  for (var i = 0; i < thunks.length; i += 1) {
    if (typeof thunks[i] !== "function") {
      throw new Error("parallel() entries must be functions");
    }
  }
  return Promise.all(thunks.map(function (thunk) {
    return Promise.resolve()
      .then(function () { return thunk(); })
      .catch(function () { return null; });
  }));
}

function pipeline(items) {
  if (!Array.isArray(items)) {
    throw new Error("pipeline() items must be an array");
  }
  if (items.length > 4096) {
    throw new Error("pipeline() supports at most 4096 items");
  }

  var stages = Array.prototype.slice.call(arguments, 1);
  for (var i = 0; i < stages.length; i += 1) {
    if (typeof stages[i] !== "function") {
      throw new Error("pipeline() stages must be functions");
    }
  }

  var chains = items.map(function (originalItem, index) {
    return (async function () {
      var previous = originalItem;
      for (var stageIndex = 0; stageIndex < stages.length; stageIndex += 1) {
        try {
          previous = await stages[stageIndex](previous, originalItem, index);
        } catch (e) {
          return null;
        }
      }
      return previous;
    })();
  });
  return Promise.all(chains);
}

function log(message) {
  var packed = JSON.parse(__log(String(message)));
  if (!packed.ok) {
    throw new Error(String(packed.error || "log() failed"));
  }
}
"""


def prepare_script(source: str) -> str:
    text = source.replace("\r\n", "\n").replace("\r", "\n")
    if text.startswith("﻿"):
        text = text[1:]
    if len(text) > _MAX_SCRIPT_CHARS:
        raise SandboxError("script exceeds PR1 size limit")
    rewritten = _EXPORT_CONST.sub("const ", text)
    leftover = _OTHER_EXPORT.search(rewritten)
    if leftover:
        raise SandboxError(
            "only `export const` at line start is rewritten; other export forms are rejected"
        )
    return rewritten


def wrap_user_script(user: str) -> str:
    return (
        PREAMBLE
        + "\nvar __done = false;\nvar __error = null;\n"
        + "(async function () {\ntry {\n"
        + user
        + "\n} catch (e) {\n__error = String(e) + (e && e.stack ? ('\\n' + e.stack) : '');\n"
        + "} finally {\n__done = true;\n}\n})();\n"
    )


def run_script(
    source: str,
    *,
    on_agent: Callable[[str, dict[str, Any]], Any],
    on_log: Callable[[str], None] | None = None,
    max_concurrency: int | None = None,
    max_agents: int = DEFAULT_MAX_AGENTS,
) -> None:
    prepared = prepare_script(source)
    wrapped = wrap_user_script(prepared)
    run_job_pump(
        wrapped,
        on_agent=on_agent,
        on_log=on_log,
        memory_limit_bytes=_MEMORY_LIMIT_BYTES,
        max_concurrency=max_concurrency,
        max_agents=max_agents,
    )
