"""Capability-restricted QuickJS host for dynamic workflow scripts.

Host bridges use JSON strings because QuickJS cannot convert Python dictionaries
into JavaScript values. QuickJS operations stay on the calling thread while
agent work runs in bounded worker threads. Child workflows are compiled by the
same pump and receive a lexical workflow function that forbids deeper nesting.

A QuickJS time limit is intentionally not set: Python callables cannot be used
while that limit is active. The external supervisor added above this layer is
responsible for wall-clock termination.
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable

from workflow.errors import SandboxError
from workflow.pump import (
    DEFAULT_MAX_AGENTS,
    PreparedWorkflow,
    run_job_pump,
)

_MAX_SCRIPT_CHARS = 256_000
_MEMORY_LIMIT_BYTES = 32 * 1024 * 1024
_EXPORT_CONST = re.compile(r"^export\s+const\s+", re.MULTILINE)
_OTHER_EXPORT = re.compile(r"^export\s+", re.MULTILINE)
_DEFAULT_ARGS = object()

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
  var ObjectKeys = Object.keys.bind(Object);

  var FunctionCtor = Function;
  var AsyncFunctionCtor =
    Object.getPrototypeOf(async function () {}).constructor;
  var GeneratorFunctionCtor =
    Object.getPrototypeOf(function* () {}).constructor;
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
  var hostWorkflow = globalThis.__workflow_start;
  var hostLog = globalThis.__log;
  var hostPhase = globalThis.__phase_set;
  var argsJson = globalThis.__workflow_args_json;
  var budgetJson = globalThis.__budget_total_json;
  delete globalThis.__agent_start;
  delete globalThis.__workflow_start;
  delete globalThis.__log;
  delete globalThis.__phase_set;
  delete globalThis.__workflow_args_json;
  delete globalThis.__budget_total_json;
  if (
    typeof hostStart !== "function" ||
    typeof hostWorkflow !== "function" ||
    typeof hostLog !== "function" ||
    typeof hostPhase !== "function"
  ) {
    throw new ErrorCtor("workflow host bridges are unavailable");
  }

  var rootArgs = JSONParse(argsJson);
  var budgetTotal = JSONParse(budgetJson);
  var budget = Object.freeze({
    total: budgetTotal,
    spent: function () { return 0; },
    remaining: function () {
      if (budgetTotal === null) return Infinity;
      return budgetTotal;
    }
  });

  var pendingAgents = ObjectCreate(null);
  var pendingWorkflows = ObjectCreate(null);
  var activeChildren = 0;
  var done = false;
  var error = null;
  var started = false;

  function errorText(value) {
    return StringValue(value) +
      (value && value.stack ? ("\n" + value.stack) : "");
  }

  function deliver(id, packedJson) {
    var rec = pendingAgents[id];
    delete pendingAgents[id];
    if (!rec) return;

    var packed;
    try {
      packed = JSONParse(packedJson);
    } catch (e) {
      rec.reject(new ErrorCtor("invalid agent completion envelope"));
      return;
    }
    if (
      !packed ||
      typeof packed !== "object" ||
      typeof packed.ok !== "boolean"
    ) {
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
        pendingAgents[id] = { resolve: resolve, reject: reject };
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
        for (
          var stageIndex = 0;
          stageIndex < stages.length;
          stageIndex += 1
        ) {
          try {
            previous = await stages[stageIndex](
              previous,
              originalItem,
              index
            );
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

  function phase(title) {
    if (typeof title !== "string" || StringTrim(title) === "") {
      throw new ErrorCtor("phase() title must be a non-empty string");
    }
    if (title.length > 80) {
      throw new ErrorCtor("phase() title must be at most 80 characters");
    }
    var packed = JSONParse(hostPhase(title));
    if (!packed.ok) {
      throw new ErrorCtor(StringValue(packed.error || "phase() failed"));
    }
  }

  function validateWorkflowSpec(spec) {
    if (
      spec === null ||
      typeof spec !== "object" ||
      ArrayIsArray(spec)
    ) {
      throw new ErrorCtor("workflow() spec must be an object");
    }
    var keys = ObjectKeys(spec);
    if (
      keys.length !== 1 ||
      keys[0] !== "scriptPath" ||
      typeof spec.scriptPath !== "string" ||
      StringTrim(spec.scriptPath) === ""
    ) {
      throw new ErrorCtor(
        "workflow() spec must be exactly {scriptPath: non-empty string}"
      );
    }
    if (spec.scriptPath.length > 4096) {
      throw new ErrorCtor("workflow() scriptPath is too long");
    }
  }

  function rootWorkflow(spec, childArgs) {
    validateWorkflowSpec(spec);
    if (childArgs === undefined) childArgs = {};

    return new PromiseCtor(function (resolve, reject) {
      try {
        var payload = JSONStringify({
          spec: { scriptPath: spec.scriptPath },
          args: childArgs
        });
        if (typeof payload !== "string") {
          reject(new ErrorCtor("workflow() args must be valid JSON"));
          return;
        }
        var id = hostWorkflow(payload);
        if (typeof id !== "string" || id === "") {
          reject(
            new ErrorCtor("workflow() host returned an invalid job id")
          );
          return;
        }
        pendingWorkflows[id] = { resolve: resolve, reject: reject };
      } catch (e) {
        reject(e);
      }
    });
  }

  function nestedWorkflow() {
    throw new ErrorCtor("nested workflow is not allowed");
  }

  function rejectWorkflow(id, message) {
    var rec = pendingWorkflows[id];
    delete pendingWorkflows[id];
    if (!rec) return;
    rec.reject(new ErrorCtor(StringValue(message || "workflow failed")));
  }

  function finishChild(id, childError) {
    var rec = pendingWorkflows[id];
    delete pendingWorkflows[id];
    activeChildren -= 1;
    if (!rec) return;
    if (childError === null) {
      rec.resolve(null);
    } else {
      rec.reject(new ErrorCtor(childError));
    }
  }

  function startChild(id, childMain, childArgsJson) {
    var rec = pendingWorkflows[id];
    if (!rec) return;
    if (typeof childMain !== "function") {
      rejectWorkflow(id, "child workflow program is not callable");
      return;
    }

    var childArgs;
    try {
      childArgs = JSONParse(childArgsJson);
    } catch (e) {
      rejectWorkflow(id, "child workflow args are invalid JSON");
      return;
    }

    activeChildren += 1;
    var childPromise = PromiseThen(
      PromiseResolve(),
      function () {
        return childMain(childArgs, budget, nestedWorkflow);
      }
    );
    PromiseThen(
      childPromise,
      function () {
        finishChild(id, null);
      },
      function (e) {
        finishChild(id, errorText(e));
      }
    );
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
  expose("workflow", nestedWorkflow);
  expose("phase", phase);
  expose("args", rootArgs);
  expose("budget", budget);

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
      function () {
        return userMain(rootArgs, budget, rootWorkflow);
      }
    );
    var caughtPromise = PromiseThen(
      userPromise,
      undefined,
      function (e) {
        error = errorText(e);
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
    return JSONStringify({
      done: done,
      error: error,
      activeChildren: activeChildren
    });
  }

  return function runtime(command, first, second, third) {
    if (command === "start") {
      start(first);
      return null;
    }
    if (command === "deliver") {
      deliver(first, second);
      return null;
    }
    if (command === "start_child") {
      startChild(first, second, third);
      return null;
    }
    if (command === "reject_workflow") {
      rejectWorkflow(first, second);
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
        raise SandboxError("script exceeds workflow size limit")
    rewritten = _EXPORT_CONST.sub("const ", text)
    leftover = _OTHER_EXPORT.search(rewritten)
    if leftover:
        raise SandboxError(
            "only `export const` at line start is rewritten; "
            "other export forms are rejected"
        )
    return rewritten


def wrap_user_script(user: str) -> str:
    return (
        "(async function (args, budget, workflow) {\n"
        + user
        + "\n})"
    )


def run_script(
    source: str,
    *,
    on_agent: Callable[[str, dict[str, Any]], Any] | None = None,
    on_log: Callable[[str], None] | None = None,
    on_phase: Callable[[str], None] | None = None,
    on_cancel: Callable[[], None] | None = None,
    prepare_agent: Callable[[str, dict[str, Any]], Any] | None = None,
    execute_agent: Callable[[Any], Any] | None = None,
    is_cached_agent: Callable[[Any], bool] | None = None,
    prepare_workflow: (
        Callable[[dict[str, Any], Any], PreparedWorkflow] | None
    ) = None,
    args: Any = _DEFAULT_ARGS,
    args_json: str | None = None,
    budget_tokens: int | None = None,
    max_concurrency: int | None = None,
    max_agents: int = DEFAULT_MAX_AGENTS,
) -> None:
    if prepare_agent is None and execute_agent is None:
        if on_agent is None:
            raise TypeError(
                "run_script requires on_agent or prepare/execute callbacks"
            )

        def default_prepare(
            prompt: str,
            opts: dict[str, Any],
        ) -> Any:
            return prompt, dict(opts)

        def default_execute(prepared: Any) -> Any:
            prompt, opts = prepared
            return on_agent(prompt, opts)

        prepare = default_prepare
        execute = default_execute
    elif (
        prepare_agent is not None
        and execute_agent is not None
        and on_agent is None
    ):
        prepare = prepare_agent
        execute = execute_agent
    else:
        raise TypeError(
            "provide either on_agent or both prepare_agent and execute_agent"
        )

    if args_json is not None and args is not _DEFAULT_ARGS:
        raise TypeError("provide either args or args_json, not both")
    if args_json is None:
        args_value = {} if args is _DEFAULT_ARGS else args
        try:
            args_json = json.dumps(
                args_value,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            )
        except (TypeError, ValueError) as exc:
            raise SandboxError("args must be valid JSON") from exc
    if (
        budget_tokens is not None
        and (
            isinstance(budget_tokens, bool)
            or not isinstance(budget_tokens, int)
            or budget_tokens < 1
        )
    ):
        raise SandboxError(
            "budget_tokens must be a positive integer"
        )

    prepared_source = prepare_script(source)
    user_function_source = wrap_user_script(prepared_source)
    run_job_pump(
        user_function_source,
        runtime_source=RUNTIME_BOOTSTRAP,
        prepare_agent=prepare,
        execute_agent=execute,
        is_cached_agent=is_cached_agent,
        prepare_workflow=prepare_workflow,
        on_log=on_log,
        on_phase=on_phase,
        on_cancel=on_cancel,
        args_json=args_json,
        budget_tokens=budget_tokens,
        memory_limit_bytes=_MEMORY_LIMIT_BYTES,
        max_concurrency=max_concurrency,
        max_agents=max_agents,
    )
