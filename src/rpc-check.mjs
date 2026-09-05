import { ethers } from "ethers";

const address = process.argv[2];
const rpcUrl = process.argv[3];

if (!address || !rpcUrl) {
  console.error("Usage: pnpm run rpc <CONTRACT_ADDRESS> <RPC_URL>");
  process.exit(1);
}

if (!ethers.isAddress(address)) {
  console.error(`Invalid EVM address: ${address}`);
  process.exit(1);
}

function hexBytes(hex) {
  return Math.max(0, (hex.length - 2) / 2);
}

try {
  const provider = new ethers.JsonRpcProvider(rpcUrl);

  console.log("========================================");
  console.log(" TermiX Provider Agent - RPC Analyzer");
  console.log("========================================\n");

  console.log(`Target : ${address}`);
  console.log(`RPC    : ${rpcUrl}\n`);

  console.log("[1/7] Checking RPC connectivity...");
  const network = await provider.getNetwork();
  console.log(`Chain ID: ${network.chainId}`);

  console.log("[2/7] Reading latest block...");
  const blockNumber = await provider.getBlockNumber();
  console.log(`Block: ${blockNumber}`);

  console.log("[3/7] Checking contract code...");
  const code = await provider.getCode(address);
  const isContract = code !== "0x";
  console.log(`Contract: ${isContract ? "YES" : "NO"}`);

  console.log("[4/7] Measuring bytecode...");
  const codeBytes = hexBytes(code);
  console.log(`Runtime bytecode: ${codeBytes} bytes`);

  console.log("[5/7] Reading native balance...");
  const balance = await provider.getBalance(address);
  console.log(`Balance: ${ethers.formatEther(balance)}`);

  console.log("[6/7] Basic risk indicators...");

  const risks = [];

  if (!isContract) {
    risks.push("ADDRESS_HAS_NO_RUNTIME_CODE");
  }

  if (isContract && codeBytes > 24000) {
    risks.push("LARGE_RUNTIME_BYTECODE");
  }

  if (risks.length === 0) {
    console.log("No basic RPC-level risk indicators detected.");
  } else {
    for (const risk of risks) {
      console.log(`- ${risk}`);
    }
  }

  console.log("[7/7] Building machine-readable result...");

  const result = {
    analyzer: "TermiX Provider Agent",
    version: "0.1.0",
    address,
    rpcUrl,
    chainId: network.chainId.toString(),
    blockNumber,
    isContract,
    runtimeBytecodeBytes: codeBytes,
    nativeBalanceWei: balance.toString(),
    nativeBalance: ethers.formatEther(balance),
    risks
  };

  console.log("\nJSON_RESULT_START");
  console.log(JSON.stringify(result, null, 2));
  console.log("JSON_RESULT_END");

  console.log("\n========================================");
  console.log(" RPC ANALYSIS COMPLETE");
  console.log("========================================");
} catch (error) {
  console.error("\nRPC analyzer failed:");
  console.error(error.shortMessage || error.message);
  process.exit(1);
}
