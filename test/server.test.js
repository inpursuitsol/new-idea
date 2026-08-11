import { describe, it } from "node:test";
import assert from "node:assert/strict";

describe("ideas", () => {
  it("assigns incremental ids", () => {
    const ideas = [];
    const create = (title) => {
      const idea = { id: ideas.length + 1, title };
      ideas.push(idea);
      return idea;
    };

    const first = create("Ship the MVP");
    const second = create("Write docs");

    assert.equal(first.id, 1);
    assert.equal(second.id, 2);
    assert.deepEqual(ideas, [
      { id: 1, title: "Ship the MVP" },
      { id: 2, title: "Write docs" },
    ]);
  });
});
