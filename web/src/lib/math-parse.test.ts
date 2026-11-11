import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { test } from "node:test";
import { markBold, parseMath } from "./math-parse.ts";

const kinds = (s: string, strict = false) => parseMath(s, strict).map((x) => `${x.kind}:${x.value}`);

test("inline, display and escaped dollars", () => {
  assert.deepEqual(kinds("If $x^2$ then"), ["text:If ", "inline:x^2", "text: then"]);
  assert.deepEqual(kinds("$$a+b$$"), ["display:a+b"]);
  assert.deepEqual(kinds("costs \\$5 and \\$6"), ["text:costs $5 and $6"]);
  assert.deepEqual(kinds("\\(y\\) here"), ["inline:y", "text: here"]);
});

test("an unmatched dollar stays literal", () => {
  assert.deepEqual(kinds("only $ one"), ["text:only $ one"]);
});

test("lenient mode (question data) keeps accepting spaced formulas", () => {
  assert.deepEqual(kinds("$ x + 1 $"), ["inline: x + 1 "]);
});

test("strict mode (AI output): currency in prose is not a formula", () => {
  const prose = "The price rose from $40 to $50, so the change is $10.";
  assert.deepEqual(kinds(prose, true), [`text:${prose}`]);
});

test("strict mode still renders real formulas next to currency", () => {
  assert.deepEqual(kinds("From $40 to $50 is $\\frac{10}{40} = 0.25$", true),
    ["text:From $40 to $50 is ", "inline:\\frac{10}{40} = 0.25"]);
  assert.deepEqual(kinds("so $x$ and $y$.", true), ["text:so ", "inline:x", "text: and ", "inline:y", "text:."]);
});

test("strict mode: closing dollar followed by a digit is not a close", () => {
  assert.deepEqual(kinds("$3 and $4", true), ["text:$3 and $4"]);
});

test("every math span in the validated dataset parses (lenient mode)", () => {
  const root = new URL("../../../data/", import.meta.url).pathname;
  const texts: string[] = [];
  const grab = (v: unknown) => { if (typeof v === "string") texts.push(v); else if (Array.isArray(v)) v.forEach(grab); else if (v && typeof v === "object") Object.values(v).forEach(grab); };
  for (const dir of ["questions", "sol", "bn"]) {
    for (const f of readdirSync(root + dir).filter((x) => x.endsWith(".json"))) grab(JSON.parse(readFileSync(`${root}${dir}/${f}`, "utf8")));
  }
  const withMath = texts.filter((t) => t.includes("$"));
  assert.ok(withMath.length > 300, `only ${withMath.length} strings contain $`);
  let spans = 0;
  for (const t of withMath) {
    for (const seg of parseMath(t)) {
      if (seg.kind !== "text") { spans++; assert.ok(seg.value.length > 0, `empty math span in: ${t.slice(0, 100)}`); }
    }
  }
  assert.ok(spans > 300, `only ${spans} math spans found`);
});

test("strict mode is not safe for question data (documents why it is AI-only)", () => {
  assert.notDeepEqual(parseMath("paid $\\$$306.", true), parseMath("paid $\\$$306.", false));
});

test("bold carries across a math span", () => {
  const runs = markBold(parseMath("**Step 1: solve $x$ now.** Then more", true));
  assert.deepEqual(runs.map((r) => `${r.bold ? "B" : "-"}${r.kind}:${r.value}`),
    ["Btext:Step 1: solve ", "Binline:x", "Btext: now.", "-text: Then more"]);
});

test("unbalanced bold marker while a reply is still streaming bolds the rest, then stops at the next marker", () => {
  assert.deepEqual(markBold(parseMath("a **b")).map((r) => `${r.bold ? "B" : "-"}${r.value}`), ["-a ", "Bb"]);
});
