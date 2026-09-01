export const meta = {
  name: "nested-child",
  description: "Child workflow sharing the parent runtime and journal",
};

phase("Child");
log("child q=" + String(args.q));
await agent("child probe q=" + String(args.q), { label: "child" });
