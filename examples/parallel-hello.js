export const meta = {
  name: "parallel-hello",
  description: "Two independent read-only probes run through parallel()",
};

const schema = {
  type: "object",
  additionalProperties: false,
  properties: {
    name: { type: "string" },
  },
  required: ["name"],
};

const results = await parallel([
  function () {
    return agent(
      "Reply with JSON only. Set name to the repository directory name. Do not write files.",
      { label: "parallel-a", schema: schema }
    );
  },
  function () {
    return agent(
      "Reply with JSON only. Set name to the repository directory name. Do not write files.",
      { label: "parallel-b", schema: schema }
    );
  },
]);

log(
  "parallel names=" +
    results.map(function (value) {
      return value === null ? "null" : value.name;
    }).join(",")
);
