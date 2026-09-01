export const meta = {
  name: "hello",
  description: "One read-only probe of the current repository identity",
};

const result = await agent(
  "Reply with JSON only. Set name to the repository directory name you are in. Do not write files.",
  {
    label: "hello",
    schema: {
      type: "object",
      additionalProperties: false,
      properties: {
        name: { type: "string" },
      },
      required: ["name"],
    },
  }
);

log("hello name=" + result.name);
