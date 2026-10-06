import { readFile } from "node:fs/promises";
import { spawnSync } from "node:child_process";
import process from "node:process";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import assert from "node:assert/strict";

const ALLOWED_ADVISORY_URL = "https://github.com/advisories/GHSA-vfj7-8cjw-p6xm";
const ALLOWED_PACKAGE = "braces";
const REVIEWED_CHAIN = [
  ["eslint-config-next", "16.3.6"],
  ["@next/eslint-plugin-next", "16.3.6"],
  ["fast-glob", "3.3.1"],
  ["micromatch", "4.0.8"],
  ["braces", "3.0.3"],
];
const REVIEWED_NAMES = new Set(REVIEWED_CHAIN.map(([name]) => name));
const HIGH_SEVERITIES = new Set(["high", "critical"]);

function fail(message) {
  throw new Error(message);
}

export function validateLock(lock) {
  if (!lock || lock.lockfileVersion !== 3 || !lock.packages || typeof lock.packages !== "object") {
    fail("package-lock.json is missing the expected lockfile v3 packages map");
  }
  const root = lock.packages[""];
  if (!root || typeof root !== "object") fail("package-lock.json is missing the root package entry");

  const production = root.dependencies ?? {};
  for (const name of ["braces", "micromatch", "fast-glob"]) {
    if (Object.prototype.hasOwnProperty.call(production, name)) {
      fail(`${name} must not be a root production dependency`);
    }
  }
  if (root.devDependencies?.["eslint-config-next"] !== "16.3.6") {
    fail("reviewed root devDependency eslint-config-next@16.3.6 changed");
  }

  const entries = new Map();
  for (const [name, version] of REVIEWED_CHAIN) {
    const entry = lock.packages[`node_modules/${name}`];
    if (!entry || entry.version !== version) fail(`reviewed dependency changed: ${name}@${version}`);
    if (entry.dev !== true) fail(`reviewed dependency is no longer dev-only: ${name}`);
    entries.set(name, entry);
  }

  const edges = [
    ["eslint-config-next", "@next/eslint-plugin-next", "16.3.6"],
    ["@next/eslint-plugin-next", "fast-glob", "3.3.1"],
    ["fast-glob", "micromatch", "^4.0.4"],
    ["micromatch", "braces", "^3.0.3"],
  ];
  for (const [parent, child, expectedRange] of edges) {
    if (entries.get(parent)?.dependencies?.[child] !== expectedRange) {
      fail(`reviewed dependency chain changed at ${parent} -> ${child}`);
    }
  }
}

function validateAuditShape(report) {
  if (!report || typeof report !== "object" || Array.isArray(report)) fail("npm audit returned malformed JSON");
  if (typeof report.auditReportVersion !== "number") fail("npm audit JSON is missing auditReportVersion");
  if (!report.vulnerabilities || typeof report.vulnerabilities !== "object" || Array.isArray(report.vulnerabilities)) {
    fail("npm audit JSON is missing vulnerabilities");
  }
  if (!report.metadata?.vulnerabilities || typeof report.metadata.vulnerabilities !== "object") {
    fail("npm audit JSON is missing vulnerability metadata");
  }
}

function advisoryLeaf(via, ownerName) {
  if (!via || typeof via !== "object" || Array.isArray(via)) fail(`malformed advisory leaf for ${ownerName}`);
  const name = via.name ?? via.dependency;
  if (name !== ALLOWED_PACKAGE || via.url !== ALLOWED_ADVISORY_URL) {
    fail(`unapproved High/Critical advisory in ${ownerName}: ${via.url ?? name ?? "unknown"}`);
  }
  if (!HIGH_SEVERITIES.has(String(via.severity ?? "").toLowerCase())) {
    fail(`allowed advisory leaf has unexpected severity for ${ownerName}`);
  }
  return ALLOWED_ADVISORY_URL;
}

function resolveLeaves(name, vulnerabilities, visiting = new Set()) {
  if (visiting.has(name)) fail(`cyclic npm audit vulnerability graph at ${name}`);
  const vuln = vulnerabilities[name];
  if (!vuln || typeof vuln !== "object") fail(`npm audit via reference is missing vulnerability ${name}`);
  if (!REVIEWED_NAMES.has(name)) fail(`High/Critical finding escaped reviewed dev chain: ${name}`);
  if (!Array.isArray(vuln.via) || vuln.via.length === 0) fail(`High/Critical finding has no advisory cause: ${name}`);

  const next = new Set(visiting);
  next.add(name);
  const leaves = new Set();
  for (const via of vuln.via) {
    if (typeof via === "string") {
      for (const leaf of resolveLeaves(via, vulnerabilities, next)) leaves.add(leaf);
    } else {
      leaves.add(advisoryLeaf(via, name));
    }
  }
  return leaves;
}

export function validateAudit(report) {
  validateAuditShape(report);
  let exceptionUsed = false;
  for (const [name, vuln] of Object.entries(report.vulnerabilities)) {
    if (!vuln || !HIGH_SEVERITIES.has(String(vuln.severity ?? "").toLowerCase())) continue;
    const leaves = resolveLeaves(name, report.vulnerabilities);
    if (leaves.size !== 1 || !leaves.has(ALLOWED_ADVISORY_URL)) {
      fail(`High/Critical finding for ${name} does not resolve solely to the allowed braces advisory`);
    }
    exceptionUsed = true;
  }
  return exceptionUsed;
}

function syntheticLock() {
  return {
    lockfileVersion: 3,
    packages: {
      "": { dependencies: { next: "16.3.6", react: "19.2.4", "react-dom": "19.2.4" }, devDependencies: { "eslint-config-next": "16.3.6" } },
      "node_modules/eslint-config-next": { version: "16.3.6", dev: true, dependencies: { "@next/eslint-plugin-next": "16.3.6" } },
      "node_modules/@next/eslint-plugin-next": { version: "16.3.6", dev: true, dependencies: { "fast-glob": "3.3.1" } },
      "node_modules/fast-glob": { version: "3.3.1", dev: true, dependencies: { micromatch: "^4.0.4" } },
      "node_modules/micromatch": { version: "4.0.8", dev: true, dependencies: { braces: "^3.0.3" } },
      "node_modules/braces": { version: "3.0.3", dev: true, dependencies: { "fill-range": "^7.1.1" } },
    },
  };
}

const allowedLeaf = { name: "braces", severity: "high", url: ALLOWED_ADVISORY_URL };
function audit(vulnerabilities) {
  return { auditReportVersion: 2, vulnerabilities, metadata: { vulnerabilities: { info: 0, low: 0, moderate: 0, high: 1, critical: 0, total: 1 } } };
}

function mustFail(fn) {
  assert.throws(fn);
}

export function runSelfTests() {
  validateLock(syntheticLock());
  assert.equal(validateAudit(audit({ braces: { severity: "high", via: [allowedLeaf] } })), true);
  assert.equal(validateAudit(audit({
    braces: { severity: "high", via: [allowedLeaf] },
    micromatch: { severity: "high", via: ["braces"] },
    "fast-glob": { severity: "high", via: ["micromatch"] },
    "@next/eslint-plugin-next": { severity: "high", via: ["fast-glob"] },
    "eslint-config-next": { severity: "high", via: ["@next/eslint-plugin-next"] },
  })), true);
  mustFail(() => validateAudit(audit({
    braces: { severity: "high", via: [allowedLeaf] },
    micromatch: { severity: "high", via: [{ name: "micromatch", severity: "high", url: "https://github.com/advisories/GHSA-other" }] },
  })));
  mustFail(() => validateAudit(audit({ other: { severity: "critical", via: [{ name: "other", severity: "critical", url: "https://github.com/advisories/GHSA-other" }] } })));
  const runtimeLock = syntheticLock();
  runtimeLock.packages[""].dependencies.braces = "3.0.3";
  mustFail(() => validateLock(runtimeLock));
  const changedLock = syntheticLock();
  changedLock.packages["node_modules/micromatch"].dependencies.braces = "^4.0.0";
  mustFail(() => validateLock(changedLock));
  mustFail(() => validateAudit({ error: { summary: "registry unavailable" } }));
  console.log("npm audit exception self-tests passed");
}

async function main() {
  if (process.argv.includes("--self-test")) {
    runSelfTests();
    return;
  }

  runSelfTests();

  const scriptDir = dirname(fileURLToPath(import.meta.url));
  const frontendDir = resolve(scriptDir, "..");
  const lock = JSON.parse(await readFile(resolve(frontendDir, "package-lock.json"), "utf8"));
  validateLock(lock);

  const result = spawnSync("npm", ["audit", "--json", "--audit-level=high", "--package-lock-only"], {
    cwd: frontendDir,
    encoding: "utf8",
    maxBuffer: 16 * 1024 * 1024,
  });
  if (result.error) fail(`npm audit could not start: ${result.error.message}`);
  if (!result.stdout?.trim()) fail(`npm audit produced no JSON${result.stderr ? `: ${result.stderr.trim()}` : ""}`);

  let report;
  try {
    report = JSON.parse(result.stdout);
  } catch {
    fail("npm audit output was not valid JSON");
  }
  const exceptionUsed = validateAudit(report);
  if (result.status !== 0 && result.status !== 1) fail(`npm audit failed with status ${result.status}`);
  if (result.status === 1 && !exceptionUsed) fail("npm audit failed without the reviewed braces exception being applicable");

  if (exceptionUsed) {
    console.warn(`WARNING: temporary audit exception used for ${ALLOWED_PACKAGE} ${ALLOWED_ADVISORY_URL}`);
  } else {
    console.log("npm audit passed with no High/Critical findings");
  }
}

const invokedDirectly = process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (invokedDirectly) {
  main().catch((error) => {
    console.error(`npm audit verification failed: ${error.message}`);
    process.exitCode = 1;
  });
}
