const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function dialog(favorites, group = ["1999"]) {
  let input;
  let select;
  let name;
  let deleteButton;
  let saveButton;
  let feedback;
  let groupInfo;
  const saved = new Map(favorites.map(item => [item.node, item.label]));
  const requests = [];
  const body = {
    set innerHTML(html) {
      this.html = html;
      const prefilled = html.match(/id="cmf-link-node-num"[\s\S]*?value="([^"]*)"/);
      input = { value: prefilled ? prefilled[1] : '', classList: { remove() {} } };
      select = {
        value: '', disabled: true, options: [],
        replaceChildren(...items) { this.options = items; },
        add(item) { this.options.push(item); },
      };
      name = { value: '' };
      deleteButton = { disabled: true };
      saveButton = { disabled: false };
      feedback = { textContent: '', className: '' };
      groupInfo = { textContent: '' };
    },
  };
  const elements = { commandModal: {}, commandModalTitleBox: {}, 'command-modal-body': body };
  const context = vm.createContext({
    document: { getElementById(id) {
      if (id === 'cmf-link-node-num') return input;
      if (id === 'cmf-link-favorite') return select;
      if (id === 'cmf-favorite-name') return name;
      if (id === 'cmf-favorite-delete') return deleteButton;
      if (id === 'cmf-favorite-save') return saveButton;
      if (id === 'cmf-favorite-feedback') return feedback;
      if (id === 'cmf-favorite-group') return groupInfo;
      return elements[id];
    } },
    bootstrap: { Modal: class { show() {} } },
    Option: class { constructor(label, value) { this.label = label; this.value = value; } },
    getAPIJSON: async url => url.endsWith("/favorite-group") ? group : favorites,
    fetch: async (url, options) => {
      const request = JSON.parse(options.body);
      requests.push({ url, request });
      if (request.action === 'delete') saved.delete(request.node);
      else {
        if (request.original_node) saved.delete(request.original_node);
        saved.set(request.node, request.label);
      }
      return { ok: true, json: async () => ({ SUCCESS: [...saved].map(([node, label]) => ({node, label})) }) };
    },
    loggedIn: true,
  });
  const source = fs.readFileSync(path.join(__dirname, '../web/js/commands.js'), 'utf8');
  vm.runInContext(source, context);
  return { context, body, requests, getInput: () => input, getSelect: () => select,
    getGroup: () => groupInfo, getName: () => name, getDelete: () => deleteButton, getFeedback: () => feedback };
}

test('favorites fill Node # only on selection, keeping row and manual entries', async () => {
  const ui = dialog([{ node: '62154', label: '<Starbase 4>' }]);
  vm.runInContext('cmdShortcut = "12345"', ui.context);
  await ui.context.openCmdModalLink(1999, 3);
  assert.equal(ui.getInput().value, '12345');
  assert.equal(ui.getSelect().disabled, false);
  assert.equal(ui.getSelect().options[1].label, '<Starbase 4> (62154)');
  assert.equal(ui.body.html.includes('<Starbase 4>'), false);

  ui.getSelect().value = '62154';
  ui.context.selectLinkFavorite();
  assert.equal(ui.getInput().value, '62154');
  assert.equal(ui.getName().value, '<Starbase 4>');
  assert.equal(ui.getDelete().disabled, false);
  ui.getInput().value = '654321';
  ui.getSelect().value = '';
  ui.context.selectLinkFavorite();
  assert.equal(ui.getInput().value, '654321');
});

test('new, save, edit, and delete remain in the link modal without connecting', async () => {
  const ui = dialog([]);
  vm.runInContext('cmdShortcut = "44444"', ui.context);
  await ui.context.openCmdModalLink(1999, 3);
  assert.equal(ui.getSelect().disabled, true);
  assert.equal(ui.getInput().value, '44444');
  ui.getName().value = 'Local hub';
  await ui.context.changeLinkFavorite(1999, 'save');
  assert.equal(ui.getSelect().value, '');
  assert.match(ui.getFeedback().textContent, /Favorite added/);
  ui.getSelect().value = '44444';
  ui.context.selectLinkFavorite();
  assert.equal(ui.requests[0].url, 'master/node/1999/favorites');
  assert.equal(ui.requests[0].request.original_node, null);

  ui.getInput().value = '55555';
  ui.getName().value = 'Renamed hub';
  await ui.context.changeLinkFavorite(1999, 'save');
  assert.equal(ui.requests[1].request.original_node, '44444');
  assert.equal(ui.getSelect().value, '55555');
  assert.equal(ui.getSelect().options[1].label, 'Renamed hub (55555)');

  await ui.context.changeLinkFavorite(1999, 'delete');
  assert.equal(ui.getSelect().disabled, true);
  assert.equal(ui.getInput().value, '55555'); // still usable for a link command
  assert.equal(ui.getName().value, '');
  assert.equal(ui.getFeedback().textContent, 'Favorite deleted.');

  ui.getInput().value = '77777';
  ui.context.newLinkFavorite();
  assert.equal(ui.getInput().value, '77777');
});

test('successive new saves append favorites instead of replacing the previous one', async () => {
  const ui = dialog([]);
  await ui.context.openCmdModalLink(1999, 3);
  for (const [node, label] of [['11111', 'First'], ['22222', 'Second'], ['33333', 'Third']]) {
    ui.getInput().value = node;
    ui.getName().value = label;
    await ui.context.changeLinkFavorite(1999, 'save');
    assert.equal(ui.requests.at(-1).request.original_node, null);
    assert.equal(ui.getSelect().value, '');
    assert.equal(ui.getName().value, '');
    assert.equal(ui.getInput().value, node);
  }
  assert.deepEqual(ui.getSelect().options.slice(1).map(x => x.value), ['11111', '22222', '33333']);
  assert.ok(ui.requests.every(x => x.url === 'master/node/1999/favorites'));
});


test('group disclosure explains automatic add/edit/delete without changing manual input', async () => {
  const ui = dialog([], ['1999', '2000']);
  vm.runInContext('cmdShortcut = "12345"', ui.context);
  await ui.context.openCmdModalLink(1999, 3);
  assert.match(ui.getGroup().textContent, /Automatically synchronized across nodes 1999, 2000/);
  assert.match(ui.getGroup().textContent, /deleting affects every node/);
  assert.equal(ui.getInput().value, '12345');
  assert.equal(ui.requests.length, 0);
});

test('ungrouped nodes report per-node scope and stale group responses are ignored', async () => {
  const ui = dialog([]);
  await ui.context.openCmdModalLink(1999, 3);
  assert.equal(ui.getGroup().textContent, 'Favorites are saved for this node only.');
  let resolve;
  ui.context.getAPIJSON = () => new Promise(r => { resolve = r; });
  const pending = ui.context.loadFavoriteGroup(1999, ui.getSelect());
  ui.body.innerHTML = ui.body.html;
  resolve(['1999', '2000']);
  await pending;
  assert.equal(ui.getGroup().textContent, '');
});
