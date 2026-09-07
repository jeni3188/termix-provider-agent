import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import http from "node:http";

import {
  observeOnce
} from "../src/provider-observer.mjs";

const tempDir =
  fs.mkdtempSync(
    path.join(
      os.tmpdir(),
      "termix-provider-observer-"
    )
  );

const responses = [
  {
    config: 503,
    jobs: 503
  },
  {
    config: 503,
    jobs: 503
  },
  {
    config: 200,
    jobs: 200
  }
];

let cycle = 0;
let postCount = 0;

const server =
  http.createServer(
    (req, res) => {
      if (
        req.method !== "GET"
      ) {
        postCount += 1;

        res.writeHead(
          405,
          {
            "content-type":
              "application/json"
          }
        );

        res.end(
          JSON.stringify({
            error:
              "POST_NOT_ALLOWED"
          })
        );

        return;
      }

      const current =
        responses[
          Math.min(
            cycle,
            responses.length - 1
          )
        ];

      const status =
        req.url ===
        "/api/v1/config"
          ? current.config
          : req.url ===
            "/api/v1/jobs"
          ? current.jobs
          : 404;

      res.writeHead(
        status,
        {
          "content-type":
            "application/json"
        }
      );

      res.end(
        JSON.stringify({
          cycle,
          status
        })
      );
    }
  );

await new Promise(
  resolve =>
    server.listen(
      0,
      "127.0.0.1",
      resolve
    )
);

const address =
  server.address();

const baseUrl =
  `http://127.0.0.1:${address.port}`;

try {
  console.log(
    "========================================"
  );

  console.log(
    " PROVIDER OBSERVER REGRESSION"
  );

  console.log(
    " DOWN -> DOWN -> HEALTHY"
  );

  console.log(
    " GET ONLY / NO POST"
  );

  console.log(
    "========================================"
  );

  const first =
    await observeOnce({
      baseUrl,
      outputDir: tempDir
    });

  assert.equal(
    first.snapshot.state,
    "BACKEND_UNAVAILABLE"
  );

  assert.equal(
    first.snapshot.previousState,
    "UNKNOWN"
  );

  assert.equal(
    first.snapshot.recovered,
    false
  );

  cycle += 1;

  const second =
    await observeOnce({
      baseUrl,
      outputDir: tempDir
    });

  assert.equal(
    second.snapshot.state,
    "BACKEND_UNAVAILABLE"
  );

  assert.equal(
    second.snapshot.previousState,
    "BACKEND_UNAVAILABLE"
  );

  assert.equal(
    second.snapshot.recovered,
    false
  );

  cycle += 1;

  const third =
    await observeOnce({
      baseUrl,
      outputDir: tempDir
    });

  assert.equal(
    third.snapshot.state,
    "HEALTHY"
  );

  assert.equal(
    third.snapshot.previousState,
    "BACKEND_UNAVAILABLE"
  );

  assert.equal(
    third.snapshot.recovered,
    true
  );

  assert.equal(
    third.snapshot.probes.config.httpStatus,
    200
  );

  assert.equal(
    third.snapshot.probes.jobs.httpStatus,
    200
  );

  assert.equal(
    postCount,
    0
  );

  for (
    const snapshot of [
      first.snapshot,
      second.snapshot,
      third.snapshot
    ]
  ) {
    assert.equal(
      snapshot.mode,
      "READ_ONLY"
    );

    assert.equal(
      snapshot.safety.getOnly,
      true
    );

    assert.equal(
      snapshot.safety.postPerformed,
      false
    );

    assert.equal(
      snapshot.safety.walletUsed,
      false
    );

    assert.equal(
      snapshot.safety.signingPerformed,
      false
    );

    assert.equal(
      snapshot.safety.broadcastPerformed,
      false
    );

    assert.equal(
      snapshot.safety.submissionPerformed,
      false
    );
  }

  const status =
    JSON.parse(
      fs.readFileSync(
        path.join(
          tempDir,
          "latest-backend-status.json"
        ),
        "utf8"
      )
    );

  assert.equal(
    status.version,
    "1.2.0"
  );

  const history =
    fs.readFileSync(
      path.join(
        tempDir,
        "observer-history.jsonl"
      ),
      "utf8"
    )
      .trim()
      .split("\n");

  assert.equal(
    history.length,
    3
  );

  console.log("");
  console.log(
    "CYCLE 1 : DOWN       PASS"
  );

  console.log(
    "CYCLE 2 : DOWN       PASS"
  );

  console.log(
    "CYCLE 3 : HEALTHY    PASS"
  );

  console.log(
    "RECOVERY             PASS"
  );

  console.log(
    "POST COUNT           : 0"
  );

  console.log(
    "GET ONLY             : PASS"
  );

  console.log(
    "SAFETY FLAGS         : PASS"
  );

  console.log("");
  console.log(
    "RESULT               : PASS"
  );

} finally {
  await new Promise(
    resolve =>
      server.close(resolve)
  );

  fs.rmSync(
    tempDir,
    {
      recursive: true,
      force: true
    }
  );
}
