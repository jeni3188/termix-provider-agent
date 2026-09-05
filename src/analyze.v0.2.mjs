import fs from "fs";

const file = process.argv[2];

if (!file) {
  console.error("Usage: pnpm analyze <SolidityFile>");
  process.exit(1);
}

if (!fs.existsSync(file)) {
  console.error(`File not found: ${file}`);
  process.exit(1);
}

const code = fs.readFileSync(file, "utf8");
const lines = code.split("\n");

const findings = [];

function addFinding(id, severity, title, message, evidence = []) {
  findings.push({
    id,
    severity,
    title,
    message,
    evidence
  });
}

function matchingLines(regex) {
  return lines
    .map((line, i) => ({ line: i + 1, text: line.trim() }))
    .filter(x => regex.test(x.text))
    .slice(0, 10);
}

/* Access control */

const txOrigin = matchingLines(/\btx\.origin\b/);

if (txOrigin.length) {
  addFinding(
    "TX-ORIGIN",
    "HIGH",
    "tx.origin authorization",
    "tx.origin is used for authorization. Prefer msg.sender and explicit access control.",
    txOrigin
  );
}

/* Dangerous execution */

const delegatecall = matchingLines(/\.delegatecall\s*\(/);

if (delegatecall.length) {
  addFinding(
    "DELEGATECALL",
    "HIGH",
    "delegatecall usage",
    "delegatecall executes code in the caller's storage context and requires strict target validation.",
    delegatecall
  );
}

const selfdestruct = matchingLines(/\bselfdestruct\s*\(/);

if (selfdestruct.length) {
  addFinding(
    "SELFDESTRUCT",
    "HIGH",
    "selfdestruct usage",
    "selfdestruct is present. Review whether this behavior is intentional and safe.",
    selfdestruct
  );
}

/* External calls */

const lowLevelCall = matchingLines(/\.call\s*(\(|\{)/);

if (lowLevelCall.length) {
  addFinding(
    "LOW-LEVEL-CALL",
    "MEDIUM",
    "Low-level call",
    "Low-level external call detected. Review target validation, return handling and reentrancy.",
    lowLevelCall
  );
}

const send = matchingLines(/\.(send|transfer)\s*\(/);

if (send.length) {
  addFinding(
    "ETH-TRANSFER",
    "LOW",
    "ETH transfer/send",
    "Review gas assumptions and recipient behavior.",
    send
  );
}

/* Reentrancy heuristic */

const externalCallIndex = lines.findIndex(line =>
  /\.call\s*(\(|\{)|\.delegatecall\s*\(/.test(line)
);

const stateAssignmentIndex = lines.findIndex(line =>
  /\b[a-zA-Z_][a-zA-Z0-9_]*\s*=\s*[^=]/.test(line)
);

if (
  externalCallIndex >= 0 &&
  stateAssignmentIndex >= 0 &&
  externalCallIndex < stateAssignmentIndex
) {
  addFinding(
    "REENTRANCY-HEURISTIC",
    "HIGH",
    "Possible checks-effects-interactions violation",
    "An external call appears before a state assignment. Review for reentrancy.",
    [{
      line: externalCallIndex + 1,
      text: lines[externalCallIndex].trim()
    }]
  );
}

/* Timestamp */

const timestamp = matchingLines(/\bblock\.timestamp\b/);

if (timestamp.length) {
  addFinding(
    "TIMESTAMP",
    "MEDIUM",
    "Block timestamp dependency",
    "block.timestamp should not be trusted for security-critical randomness or strict timing assumptions.",
    timestamp
  );
}

/* msg.value */

const msgValue = matchingLines(/\bmsg\.value\b/);

if (msgValue.length) {
  addFinding(
    "MSG-VALUE",
    "MEDIUM",
    "Ether value handling",
    "Contract uses msg.value. Review payable functions, accounting and unexpected ETH.",
    msgValue
  );
}

/* unchecked */

const unchecked = matchingLines(/\bunchecked\s*\{/);

if (unchecked.length) {
  addFinding(
    "UNCHECKED",
    "MEDIUM",
    "Unchecked arithmetic",
    "unchecked arithmetic detected. Verify overflow/underflow assumptions.",
    unchecked
  );
}

/* Authorization */

const authFunctions = matchingLines(
  /\b(onlyOwner|onlyAdmin|owner|admin|AccessControl|hasRole)\b/
);

if (!authFunctions.length) {
  addFinding(
    "ACCESS-CONTROL-REVIEW",
    "MEDIUM",
    "Authorization review required",
    "No obvious access-control mechanism was detected. Manually review privileged functions."
  );
}

/* Summary */

const summary = {
  total: findings.length,
  critical: findings.filter(x => x.severity === "CRITICAL").length,
  high: findings.filter(x => x.severity === "HIGH").length,
  medium: findings.filter(x => x.severity === "MEDIUM").length,
  low: findings.filter(x => x.severity === "LOW").length
};

const report = {
  analyzer: "TermiX Provider Agent",
  version: "0.2.0",
  file,
  bytes: Buffer.byteLength(code),
  lines: lines.length,
  findings,
  summary
};

console.log(JSON.stringify(report, null, 2));
