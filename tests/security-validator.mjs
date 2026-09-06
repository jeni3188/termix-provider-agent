import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";

const root = process.cwd();
const approvalDir = path.join(
  root,
  "provider-output/demo-security-fair-001"
);

const approvalFiles = fs.readdirSync(approvalDir)
  .filter((name) =>
    name.startsWith("OFFER-APPROVAL-approval-") &&
    name.endsWith(".json")
  )
  .sort();

if (approvalFiles.length === 0) {
  console.error(`No approval artifact found: ${approvalDir}`);
  process.exit(2);
}

const approval = path.join(
  approvalDir,
  approvalFiles[approvalFiles.length - 1]
);

console.log(`Approval fixture: ${path.basename(approval)}`);

const validator = path.join(root, "src/aacp-validate.mjs");
const tmpDir = "/tmp/termix-security-tests";

fs.rmSync(tmpDir, { recursive: true, force: true });
fs.mkdirSync(tmpDir, { recursive: true });

if (!fs.existsSync(approval)) {
  console.error(`Approval file not found: ${approval}`);
  process.exit(2);
}

const original = JSON.parse(fs.readFileSync(approval, "utf8"));
let passed = 0;
let failed = 0;

function run(name, mutate, expected) {
  const file = path.join(
    tmpDir,
    name.toLowerCase().replace(/[^a-z0-9]+/g, "-") + ".json"
  );

  const data = structuredClone(original);
  mutate(data);
  fs.writeFileSync(file, JSON.stringify(data, null, 2));

  let output = "";
  let code = 0;

  try {
    output = execFileSync("node", [validator, file], {
      cwd: root,
      encoding: "utf8",
      stdio: ["ignore", "pipe", "pipe"],
    });
  } catch (err) {
    code = err.status ?? 1;
    output = `${err.stdout ?? ""}${err.stderr ?? ""}`;
  }

  const ok =
    expected === "PASS"
      ? code === 0 && /VALIDATION PASSED/.test(output)
      : code !== 0 && /VALIDATION BLOCKED|VALIDATION FAILED/.test(output);

  if (ok) {
    passed++;
    console.log(`PASS: ${name}`);
  } else {
    failed++;
    console.log(`FAIL: ${name}`);
    console.log(output.trim());
  }
}

console.log("========================================");
console.log(" TERMIX AACP VALIDATOR SECURITY TEST");
console.log(" READ ONLY / NO NETWORK");
console.log("========================================");
console.log("");

run("Original approval", () => {}, "PASS");

run("Tampered price", (d) => {
  d.pricing.price = "499000000";
}, "BLOCK");

run("Tampered job ID", (d) => {
  d.job.jobId = "tampered-job-001";
}, "BLOCK");

run("Tampered budget", (d) => {
  d.pricing.budget = "600000000";
}, "BLOCK");

run("Submitted flag", (d) => {
  d.execution = d.execution ?? {};
  d.execution.offerSubmitted = true;
}, "BLOCK");

run("Signed flag", (d) => {
  d.execution = d.execution ?? {};
  d.execution.transactionSigned = true;
}, "BLOCK");

run("Broadcast flag", (d) => {
  d.execution = d.execution ?? {};
  d.execution.transactionBroadcast = true;
}, "BLOCK");

console.log("");
console.log("========================================");
console.log(" SECURITY TEST SUMMARY");
console.log("========================================");
console.log(`Passed: ${passed}/7`);
console.log(`Failed: ${failed}/7`);

if (failed === 0) {
  console.log("");
  console.log("ALL SECURITY VALIDATOR TESTS PASSED");
  console.log("");
  console.log("Original approval : ACCEPTED");
  console.log("Tampering         : BLOCKED");
  console.log("Network           : NONE");
  console.log("Wallet            : NOT USED");
  console.log("Signing           : NOT USED");
  console.log("Broadcast         : NOT USED");
  process.exit(0);
}

process.exit(1);
