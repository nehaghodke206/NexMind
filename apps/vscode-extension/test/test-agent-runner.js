const assert = require('assert');
const path = require('path');
const cp = require('child_process');
const fs = require('fs');

async function runTests() {
  console.log('--- Testing Agent Runner and Bundled Binary ---');

  const extensionDir = path.resolve(__dirname, '..');
  const binaryName = process.platform === 'win32' ? 'dependency-guardian.exe' : 'dependency-guardian';
  const binaryPath = path.join(extensionDir, 'bin', binaryName);

  console.log(`Checking binary existence at: ${binaryPath}`);
  assert.ok(fs.existsSync(binaryPath), `Binary must exist at ${binaryPath}`);

  const baselineFixture = path.resolve(extensionDir, '../../agents/detection/tests/fixtures/baseline.json');
  const pathRemovedFixture = path.resolve(extensionDir, '../../agents/detection/tests/fixtures/path_removed.json');
  const identicalFixture = path.resolve(extensionDir, '../../agents/detection/tests/fixtures/identical.json');

  assert.ok(fs.existsSync(baselineFixture), 'Baseline fixture must exist');
  assert.ok(fs.existsSync(pathRemovedFixture), 'Path removed fixture must exist');

  // Test 1: Run identical specifications
  console.log('Test 1: Running binary on identical specs...');
  const resIdentical = cp.spawnSync(binaryPath, [baselineFixture, identicalFixture, '--format', 'json'], {
    encoding: 'utf-8',
    timeout: 10000,
  });
  assert.strictEqual(resIdentical.status, 0, `Process failed: ${resIdentical.stderr}`);
  const jsonIdentical = JSON.parse(resIdentical.stdout.slice(resIdentical.stdout.indexOf('{')));
  assert.strictEqual(jsonIdentical.success, true);
  assert.strictEqual(jsonIdentical.summary.total_findings, 0);
  console.log('  -> Passed! (0 findings)');

  // Test 2: Run path removed specification
  console.log('Test 2: Running binary on path_removed fixture...');
  const resBreaking = cp.spawnSync(binaryPath, [baselineFixture, pathRemovedFixture, '--format', 'json'], {
    encoding: 'utf-8',
    timeout: 10000,
  });
  assert.strictEqual(resBreaking.status, 0, `Process failed: ${resBreaking.stderr}`);
  const jsonBreaking = JSON.parse(resBreaking.stdout.slice(resBreaking.stdout.indexOf('{')));
  assert.strictEqual(jsonBreaking.success, true);
  assert.strictEqual(jsonBreaking.summary.breaking_count, 1);
  assert.strictEqual(jsonBreaking.findings[0].rule_id, 'RULE-PATH-REMOVED');
  assert.strictEqual(jsonBreaking.findings[0].compatibility, 'breaking');
  assert.strictEqual(jsonBreaking.findings[0].confidence, 1.0);
  console.log('  -> Passed! (1 breaking change detected: RULE-PATH-REMOVED)');

  // Test 3: Run with mock provider in hybrid mode
  console.log('Test 3: Running binary in hybrid mode with mock provider...');
  const resHybrid = cp.spawnSync(
    binaryPath,
    [baselineFixture, pathRemovedFixture, '--mode', 'hybrid', '--provider', 'mock', '--format', 'json'],
    { encoding: 'utf-8', timeout: 10000 }
  );
  assert.strictEqual(resHybrid.status, 0, `Process failed: ${resHybrid.stderr}`);
  const jsonHybrid = JSON.parse(resHybrid.stdout.slice(resHybrid.stdout.indexOf('{')));
  assert.strictEqual(jsonHybrid.mode, 'hybrid');
  assert.strictEqual(jsonHybrid.ai_status, 'completed');
  assert.strictEqual(jsonHybrid.summary.breaking_count, 1);
  console.log('  -> Passed! (Hybrid mode completed with mock AI)');

  // Test 4: --fail-on-breaking flag exit code
  console.log('Test 4: Running binary with --fail-on-breaking flag...');
  const resFailOnBreaking = cp.spawnSync(
    binaryPath,
    [baselineFixture, pathRemovedFixture, '--fail-on-breaking', '--quiet'],
    { encoding: 'utf-8', timeout: 10000 }
  );
  assert.strictEqual(resFailOnBreaking.status, 1, 'Should exit with code 1 on breaking changes');
  console.log('  -> Passed! (Exited with code 1)');

  console.log('\nAll Agent Runner & Bundled Binary tests PASSED successfully!');
}

runTests().catch((err) => {
  console.error('Test execution failed:', err);
  process.exit(1);
});

