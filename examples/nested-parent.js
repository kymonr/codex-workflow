export const meta = {
  name: "nested-parent",
  description: "One parent agent followed by a one-level child workflow",
};

phase("Parent");
await agent("parent probe", { label: "parent" });

await workflow(
  { scriptPath: "nested-child.js" },
  { q: args.q === undefined ? 1 : args.q }
);

log("nested workflow complete");
