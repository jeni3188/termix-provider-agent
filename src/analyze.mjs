import fs from "fs";

const file = process.argv[2];

if (!file) {
  console.error("Usage: pnpm run analyze <SolidityFile>");
  process.exit(1);
}

if (!fs.existsSync(file)) {
  console.error(`File not found: ${file}`);
  process.exit(1);
}

const code = fs.readFileSync(file, "utf8");
const lines = code.split("\n");

const findings = [];

function addFinding(
  id,
  severity,
  confidence,
  title,
  message,
  evidence = []
) {
  findings.push({
    id,
    severity,
    confidence,
    title,
    message,
    evidence
  });
}

function matchingLines(regex, limit = 10) {
  return lines
    .map((line, i) => ({
      line: i + 1,
      text: line.trim()
    }))
    .filter(x => regex.test(x.text))
    .slice(0, limit);
}

function has(regex) {
  return regex.test(code);
}

/* =========================================================
   HIGH RISK
   ========================================================= */

/* tx.origin */
const txOrigin = matchingLines(/\btx\.origin\b/);

if (txOrigin.length) {
  addFinding(
    "TX-ORIGIN",
    "HIGH",
    "HIGH",
    "tx.origin authorization",
    "tx.origin is used. Authorization should generally rely on msg.sender and explicit access control.",
    txOrigin
  );
}

/* delegatecall */
const delegatecall = matchingLines(/\.delegatecall\s*\(/);

if (delegatecall.length) {
  addFinding(
    "DELEGATECALL",
    "HIGH",
    "HIGH",
    "delegatecall usage",
    "delegatecall executes target code in the caller's storage context. Target validation and upgrade controls require review.",
    delegatecall
  );
}

/* selfdestruct */
const selfdestruct = matchingLines(/\bselfdestruct\s*\(/);

if (selfdestruct.length) {
  addFinding(
    "SELFDESTRUCT",
    "HIGH",
    "HIGH",
    "selfdestruct usage",
    "selfdestruct behavior requires explicit review because it can permanently alter contract behavior and ETH handling.",
    selfdestruct
  );
}

/* Inline assembly */
const assembly = matchingLines(/\bassembly\s*\{/);

if (assembly.length) {
  addFinding(
    "INLINE-ASSEMBLY",
    "HIGH",
    "MEDIUM",
    "Inline assembly",
    "Inline assembly bypasses many Solidity safety checks and should receive focused manual review.",
    assembly
  );
}

/* =========================================================
   EXTERNAL CALLS
   ========================================================= */

const lowLevelCall = matchingLines(/\.call\s*(\(|\{)/);

if (lowLevelCall.length) {
  addFinding(
    "LOW-LEVEL-CALL",
    "MEDIUM",
    "HIGH",
    "Low-level call",
    "Low-level external call detected. Review target validation, return handling and reentrancy protection.",
    lowLevelCall
  );
}

const staticcall = matchingLines(/\.staticcall\s*\(/);

if (staticcall.length) {
  addFinding(
    "STATICCALL",
    "LOW",
    "HIGH",
    "staticcall usage",
    "staticcall interacts with external code. Verify target trust assumptions and failure handling.",
    staticcall
  );
}

/* =========================================================
   TIMING / BLOCK DATA
   ========================================================= */

const timestamp = matchingLines(/\bblock\.timestamp\b/);

if (timestamp.length) {
  addFinding(
    "TIMESTAMP",
    "MEDIUM",
    "HIGH",
    "Block timestamp dependency",
    "block.timestamp should not be treated as secure randomness or as an exact timing source.",
    timestamp
  );
}

const blockNumber = matchingLines(/\bblock\.number\b/);

if (blockNumber.length) {
  addFinding(
    "BLOCK-NUMBER",
    "LOW",
    "HIGH",
    "Block number dependency",
    "Contract depends on block.number. Review assumptions involving timing, randomness or chain progression.",
    blockNumber
  );
}

/* =========================================================
   VALUE / ETH HANDLING
   ========================================================= */

const msgValue = matchingLines(/\bmsg\.value\b/);

if (msgValue.length) {
  addFinding(
    "MSG-VALUE",
    "MEDIUM",
    "HIGH",
    "Ether value handling",
    "Contract uses msg.value. Review payable functions, accounting and unexpected ETH.",
    msgValue
  );
}

const transfer = matchingLines(/\.(send|transfer)\s*\(/);

if (transfer.length) {
  addFinding(
    "ETH-TRANSFER",
    "LOW",
    "HIGH",
    "ETH send/transfer",
    "ETH transfer detected. Review gas assumptions and recipient behavior.",
    transfer
  );
}

/* =========================================================
   UNCHECKED ARITHMETIC
   ========================================================= */

const unchecked = matchingLines(/\bunchecked\s*\{/);

if (unchecked.length) {
  addFinding(
    "UNCHECKED",
    "MEDIUM",
    "HIGH",
    "Unchecked arithmetic",
    "Unchecked arithmetic detected. Verify overflow/underflow assumptions.",
    unchecked
  );
}

/* =========================================================
   REENTRANCY HEURISTICS
   ========================================================= */

const externalCallIndexes = [];

lines.forEach((line, i) => {
  if (
    /\.call\s*(\(|\{)/.test(line) ||
    /\.delegatecall\s*\(/.test(line) ||
    /\.(send|transfer)\s*\(/.test(line)
  ) {
    externalCallIndexes.push(i);
  }
});

const stateWriteRegex =
  /\b[a-zA-Z_][a-zA-Z0-9_]*(\[[^\]]+\])?\s*(\+=|-=|\*=|\/=|%=|=)\s*[^=]/;

const stateWriteIndexes = [];

lines.forEach((line, i) => {
  if (stateWriteRegex.test(line)) {
    stateWriteIndexes.push(i);
  }
});

if (externalCallIndexes.length && stateWriteIndexes.length) {
  const suspicious = externalCallIndexes.some(callIndex =>
    stateWriteIndexes.some(stateIndex =>
      stateIndex > callIndex &&
      stateIndex - callIndex <= 12
    )
  );

  if (suspicious) {
    const idx = externalCallIndexes.find(callIndex =>
      stateWriteIndexes.some(
        stateIndex =>
          stateIndex > callIndex &&
          stateIndex - callIndex <= 12
      )
    );

    addFinding(
      "REENTRANCY-HEURISTIC",
      "HIGH",
      "LOW",
      "Possible reentrancy pattern",
      "An external interaction appears before a nearby state write. Review checks-effects-interactions ordering and reentrancy guards.",
      [{
        line: idx + 1,
        text: lines[idx].trim()
      }]
    );
  }
}

/* =========================================================
   ACCESS CONTROL
   ========================================================= */

const accessControlIndicators = matchingLines(
  /\b(onlyOwner|onlyAdmin|onlyRole|hasRole|AccessControl|Ownable)\b/
);

const privilegedIndicators = matchingLines(
  /\b(function|modifier)\b.*\b(admin|owner|upgrade|withdraw|mint|pause|unpause|set[A-Z])/i
);

if (!accessControlIndicators.length && privilegedIndicators.length) {
  addFinding(
    "ACCESS-CONTROL-REVIEW",
    "HIGH",
    "LOW",
    "Privileged function without obvious access control",
    "A potentially privileged function was detected without an obvious ownership or role-based access-control mechanism.",
    privilegedIndicators
  );
} else if (!accessControlIndicators.length) {
  addFinding(
    "ACCESS-CONTROL-REVIEW",
    "MEDIUM",
    "LOW",
    "Authorization review required",
    "No obvious access-control mechanism was detected. Manually review privileged functions."
  );
}

/* =========================================================
   PROXY / UPGRADE INDICATORS
   ========================================================= */

const proxyIndicators = matchingLines(
  /\b(delegatecall|implementation|upgradeTo|upgradeToAndCall|ERC1967|TransparentUpgradeableProxy|UUPS)\b/
);

if (proxyIndicators.length && !delegatecall.length) {
  addFinding(
    "PROXY-REVIEW",
    "MEDIUM",
    "MEDIUM",
    "Proxy or upgradeability indicators",
    "Upgrade/proxy-related patterns were detected. Review implementation authorization and upgrade safety.",
    proxyIndicators
  );
}

/* =========================================================
   RANDOMNESS
   ========================================================= */

const randomness = matchingLines(
  /\b(block\.timestamp|block\.number|blockhash\s*\()/
);

if (
  randomness.length &&
  /\b(random|randomness|lottery|winner|seed)\b/i.test(code)
) {
  addFinding(
    "WEAK-RANDOMNESS",
    "HIGH",
    "MEDIUM",
    "Potential weak randomness",
    "Block-derived values appear near randomness-related logic. Block values should not be considered secure randomness.",
    randomness
  );
}

/* =========================================================
   FALLBACK / RECEIVE
   ========================================================= */

const fallbackFunctions = matchingLines(
  /\b(fallback|receive)\s*\(/
);

if (fallbackFunctions.length) {
  addFinding(
    "FALLBACK-RECEIVE",
    "LOW",
    "HIGH",
    "Fallback or receive function",
    "Fallback/receive logic detected. Review unexpected calls and ETH reception behavior.",
    fallbackFunctions
  );
}

/* =========================================================
   RISK SCORE
   ========================================================= */

const weights = {
  CRITICAL: 10,
  HIGH: 7,
  MEDIUM: 4,
  LOW: 1
};

const score = findings.reduce(
  (sum, finding) => sum + (weights[finding.severity] || 0),
  0
);

let riskLevel = "LOW";

if (score >= 20) {
  riskLevel = "CRITICAL";
} else if (score >= 12) {
  riskLevel = "HIGH";
} else if (score >= 5) {
  riskLevel = "MEDIUM";
}

/* =========================================================
   SUMMARY
   ========================================================= */

const summary = {
  total: findings.length,
  critical: findings.filter(x => x.severity === "CRITICAL").length,
  high: findings.filter(x => x.severity === "HIGH").length,
  medium: findings.filter(x => x.severity === "MEDIUM").length,
  low: findings.filter(x => x.severity === "LOW").length,
  riskScore: score,
  riskLevel
};

const report = {
  analyzer: "TermiX Provider Agent",
  version: "0.3.0",
  file,
  bytes: Buffer.byteLength(code),
  lines: lines.length,
  findings,
  summary
};

console.log(JSON.stringify(report, null, 2));
