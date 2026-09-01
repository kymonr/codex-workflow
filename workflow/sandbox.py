"""Capability-restricted QuickJS host for one workflow script.

Host bridges use JSON strings because QuickJS cannot convert Python dicts into
JavaScript values. QuickJS operations stay on the calling thread while agent
work runs in bounded worker threads. A time limit is intentionally not set:
QuickJS forbids Python callables while one is active.
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

RUNTIME_BOOTSTRAP = r"""
(function () {
  var JSONParse = JSON.parse.bind(JSON);
  var JSONStringify = JSON.stringify.bind(JSON);
  var ArrayCtor = Array;
  var ArrayIsArray = Array.isArray;
  var ArrayMap = Function.call.bind(Array.prototype.map);
  var ArraySlice = Function.call.bind(Array.prototype.slice);
  var StringTrim = Function.call.bind(String.prototype.trim);
  var PromiseCtor = Promise;
  var PromiseResolve = Promise.resolve.bind(Promise);
  var PromiseThen = Function.call.bind(Promise.prototype.then);
  var StringValue = String;
  var ErrorCtor = Error;
  var ObjectCreate = Object.create;

  var FunctionCtor = Function;
  var AsyncFunctionCtor = Object.getPrototypeOf(async function () {}).constructor;
  var GeneratorFunctionCtor = Object.getPrototypeOf(function* () {}).constructor;
  var AsyncGeneratorFunctionCtor =
    Object.getPrototypeOf(async function* () {}).constructor;

  function deny(name) {
    return function () {
      throw new ErrorCtor(name + " is disabled in workflow sandbox");
    };
  }

  function lockConstructor(ctor, name) {
    Object.defineProperty(ctor.prototype, "constructor", {
      value: deny(name),
      writable: false,
      configurable: false,
      enumerable: false
    });
  }

  lockConstructor(FunctionCtor, "Function");
  lockConstructor(AsyncFunctionCtor, "AsyncFunction");
  lockConstructor(GeneratorFunctionCtor, "GeneratorFunction");
  lockConstructor(AsyncGeneratorFunctionCtor, "AsyncGeneratorFunction");

  Object.defineProperty(globalThis, "Function", {
    value: deny("Function"),
    writable: false,
    configurable: false,
    enumerable: false
  });
  Object.defineProperty(globalThis, "eval", {
    value: deny("eval"),
    writable: false,
    configurable: false,
    enumerable: false
  });

  Object.freeze(PromiseCtor.prototype);
  Object.freeze(PromiseCtor);
  Object.defineProperty(globalThis, "Promise", {
    value: PromiseCtor,
    writable: false,
    configurable: false,
    enumerable: false
  });

  function DisabledDate() {
    throw new ErrorCtor("Date is disabled in workflow sandbox");
  }
  DisabledDate.now = deny("Date.now");
  DisabledDate.parse = deny("Date.parse");
  DisabledDate.UTC = deny("Date.UTC");
  Object.freeze(DisabledDate);
  Object.defineProperty(globalThis, "Date", {
    value: DisabledDate,
    writable: false,
    configurable: false,
    enumerable: false
  });

  Object.defineProperty(Math, "random", {
    value: deny("Math.random"),
    writable: false,
    configurable: false,
    enumerable: false
  });
  Object.freeze(Math);
  Object.defineProperty(globalThis, "Math", {
    value: Math,
    writable: false,
    configurable: false,
    enumerable: false
  });

  var hostStart = globalThis.__agent_start;
  var hostLog = globalThis.__log;
  delete globalThis.__agent_start;
  delete globalThis.__log;
  if (typeof hostStart !== "function" || typeof hostLog !== "function") {
    throw new ErrorCtor("workflow host bridges are unavailable");
  }

  var pending = ObjectCreate(null);
  var done = false;
  var error = null;
  var started = false;

  function deliver(id, packedJson) {
    var rec = pending[id];
    delete pending[id];
    if (!rec) return;

    var packed;
    try {
      packed = JSONParse(packedJson);
    } catch (e) {
      rec.reject(new ErrorCtor("invalid agent completion envelope"));
      return;
    }
    if (!packed || typeof packed !== "object" || typeof packed.ok !== "boolean") {
      rec.reject(new ErrorCtor("invalid agent completion envelope"));
      return;
    }
    if (!packed.ok) {
      rec.reject(new ErrorCtor(StringValue(packed.error || "agent failed")));
    } else {
      rec.resolve(packed.value);
    }
  }

  function allValues(values) {
    return new PromiseCtor(function (resolve, reject) {
      var length = values.length;
      var results = new ArrayCtor(length);
      if (length === 0) {
        resolve(results);
        return;
      }

      var remaining = length;
      for (var i = 0; i < length; i += 1) {
        (function (index) {
          var candidate;
          try {
            candidate = PromiseResolve(values[index]);
          } catch (e) {
            reject(e);
            return;
          }
          PromiseThen(
            candidate,
            function (value) {
              results[index] = value;
              remaining -= 1;
              if (remaining === 0) {
                resolve(results);
              }
            },
            reject
          );
        })(i);
      }
    });
  }

  function agent(prompt, opts) {
    if (typeof prompt !== "string") {
      throw new ErrorCtor("agent() prompt must be a string");
    }
    if (StringTrim(prompt) === "") {
      throw new ErrorCtor("agent() prompt must be non-empty");
    }
    if (opts === undefined || opts === null) {
      opts = {};
    } else if (typeof opts !== "object" || ArrayIsArray(opts)) {
      throw new ErrorCtor("agent() opts must be an object");
    }

    return new PromiseCtor(function (resolve, reject) {
      try {
        var payload = JSONStringify({ prompt: prompt, opts: opts });
        var id = hostStart(payload);
        if (typeof id !== "string" || id === "") {
          reject(new ErrorCtor("agent() host returned an invalid job id"));
          return;
        }
        pending[id] = { resolve: resolve, reject: reject };
      } catch (e) {
        reject(e);
      }
    });
  }

  function parallel(thunks) {
    if (!ArrayIsArray(thunks)) {
      throw new ErrorCtor("parallel() expects an array of functions");
    }
    if (thunks.length > 4096) {
      throw new ErrorCtor("parallel() supports at most 4096 entries");
    }
    for (var i = 0; i < thunks.length; i += 1) {
      if (typeof thunks[i] !== "function") {
        throw new ErrorCtor("parallel() entries must be functions");
      }
    }
    return allValues(ArrayMap(thunks, function (thunk) {
      var startedThunk = PromiseThen(
        PromiseResolve(),
        function () { return thunk(); }
      );
      return PromiseThen(
        startedThunk,
        undefined,
        function () { return null; }
      );
    }));
  }

  function pipeline(items) {
    if (!ArrayIsArray(items)) {
      throw new ErrorCtor("pipeline() items must be an array");
    }
    if (items.length > 4096) {
      throw new ErrorCtor("pipeline() supports at most 4096 items");
    }

    var stages = ArraySlice(arguments, 1);
    for (var i = 0; i < stages.length; i += 1) {
      if (typeof stages[i] !== "function") {
        throw new ErrorCtor("pipeline() stages must be functions");
      }
    }

    var chains = ArrayMap(items, function (originalItem, index) {
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
    return allValues(chains);
  }

  function log(message) {
    var packed = JSONParse(hostLog(StringValue(message)));
    if (!packed.ok) {
      throw new ErrorCtor(StringValue(packed.error || "log() failed"));
    }
  }

  function notInPr2(name) {
    return function () {
      throw new ErrorCtor(name + " is not available in PR2");
    };
  }

  function expose(name, value) {
    Object.defineProperty(globalThis, name, {
      value: value,
      writable: false,
      configurable: false,
      enumerable: true
    });
  }

  expose("agent", agent);
  expose("parallel", parallel);
  expose("pipeline", pipeline);
  expose("log", log);
  expose("workflow", notInPr2("workflow()"));
  expose("phase", notInPr2("phase()"));

  function start(userMain) {
    if (started) {
      throw new ErrorCtor("workflow script already started");
    }
    if (typeof userMain !== "function") {
      throw new ErrorCtor("workflow user program is not callable");
    }
    started = true;
    var userPromise = PromiseThen(
      PromiseResolve(),
      function () { return userMain(); }
    );
    var caughtPromise = PromiseThen(
      userPromise,
      undefined,
      function (e) {
        error = StringValue(e) + (e && e.stack ? ("\n" + e.stack) : "");
      }
    );
    PromiseThen(
      caughtPromise,
      function () {
        done = true;
      }
    );
  }

  function stateJson() {
    return JSONStringify({ done: done, error: error });
  }

  return function runtime(command, first, second) {
    if (command === "start") {
      start(first);
      return null;
    }
    if (command === "deliver") {
      deliver(first, second);
      return null;
    }
    if (command === "state") {
      return stateJson();
    }
    throw new ErrorCtor("unknown workflow runtime command");
  };
})()
"""

# Backward-compatible name for code that imported the old constant.
PREAMBLE = RUNTIME_BOOTSTRAP


def prepare_script(source: str) -> str:
    text = source.replace("\r\n", "\n").replace("\r", "\n")
    if text.startswith("﻿"):
        text = text[1:]
    if len(text) > _MAX_SCRIPT_CHARS:
        raise SandboxError("script exceeds PR2 size limit")
    rewritten = _EXPORT_CONST.sub("const ", text)
    leftover = _OTHER_EXPORT.search(rewritten)
    if leftover:
        raise SandboxError(
            "only `export const` at line start is rewritten; other export forms are rejected"
        )
    return rewritten


def wrap_user_script(user: str) -> str:
    return "(async function () {\n" + user + "\n})"


def run_script(
    source: str,
    *,
    on_agent: Callable[[str, dict[str, Any]], Any] | None = None,
    on_log: Callable[[str], None] | None = None,
    prepare_agent: Callable[[str, dict[str, Any]], Any] | None = None,
    execute_agent: Callable[[Any], Any] | None = None,
    max_concurrency: int | None = None,
    max_agents: int = DEFAULT_MAX_AGENTS,
) -> None:
    if prepare_agent is None and execute_agent is None:
        if on_agent is None:
            raise TypeError("run_script requires on_agent or prepare/execute callbacks")

        def default_prepare(prompt: str, opts: dict[str, Any]) -> Any:
            return prompt, dict(opts)

        def default_execute(prepared: Any) -> Any:
            prompt, opts = prepared
            return on_agent(prompt, opts)

        prepare = default_prepare
        execute = default_execute
    elif prepare_agent is not None and execute_agent is not None and on_agent is None:
        prepare = prepare_agent
        execute = execute_agent
    else:
        raise TypeError(
            "provide either on_agent or both prepare_agent and execute_agent"
        )

    prepared_source = prepare_script(source)
    user_function_source = wrap_user_script(prepared_source)
    run_job_pump(
        user_function_source,
        runtime_source=RUNTIME_BOOTSTRAP,
        prepare_agent=prepare,
        execute_agent=execute,
        on_log=on_log,
        memory_limit_bytes=_MEMORY_LIMIT_BYTES,
        max_concurrency=max_concurrency,
        max_agents=max_agents,
    )
