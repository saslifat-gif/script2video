const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const path = require('node:path');
const { test } = require('node:test');
const vm = require('node:vm');

function studio() {
  const nodes = new Map();
  const context = vm.createContext({
    document: {
      querySelector(selector) {
        if (!nodes.has(selector)) nodes.set(selector, {
          addEventListener() {},
          classList: { remove() {} },
          hidden: true,
          textContent: '',
        });
        return nodes.get(selector);
      },
    },
    // Leave bootstrap pending; these tests exercise completion and API requests.
    fetch: () => new Promise(() => {}),
  });
  vm.runInContext(readFileSync(path.join(__dirname,
    '../src/script2video/web_static/app.js'), 'utf8'), context);
  vm.runInContext('updateInterface = () => {};', context);
  return { context, nodes };
}

test('completion shows timing warnings and clears them for the next clean job', () => {
  const { context, nodes } = studio();
  context.job = { output: '/output', files: ['narration.wav'],
    warnings: ['Narration is 0.10 seconds shorter than the video.'] };
  vm.runInContext('finishSuccessfully(job)', context);
  assert.equal(nodes.get('#success-panel').hidden, false);
  assert.equal(nodes.get('#success-warning').hidden, false);
  assert.match(nodes.get('#success-warning').textContent, /0.10 seconds shorter/);
  assert.match(nodes.get('#success-title').textContent, /review timing/);
  assert.match(nodes.get('#status-chip').innerHTML, /Review timing/);
  context.job.warnings = [];
  vm.runInContext('finishSuccessfully(job)', context);
  assert.equal(nodes.get('#success-warning').hidden, true);
  assert.equal(nodes.get('#success-warning').textContent, '');
  assert.equal(nodes.get('#success-title').textContent, 'Your files are ready');
  assert.match(nodes.get('#status-chip').innerHTML, /Complete/);
});

test('mutating requests send the bootstrapped token along with JSON', async () => {
  const { context } = studio();
  let sent;
  context.fetch = async (url, options) => {
    sent = { url, options };
    return { ok: true, json: async () => ({ opened: true }) };
  };
  vm.runInContext('state.bootstrap = { csrf_token: "session-token" };', context);
  await vm.runInContext('api("/api/open-output", { method: "POST", ' +
    'body: JSON.stringify({path: "/output"}) })', context);
  assert.equal(sent.options.headers['X-Studio-Token'], 'session-token');
  assert.equal(sent.options.headers['Content-Type'], 'application/json');
  assert.equal(sent.options.method, 'POST');
  assert.equal(JSON.parse(sent.options.body).path, '/output');
});
