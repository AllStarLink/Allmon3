function audioDate(seconds) { return new Date(seconds * 1000).toLocaleString(undefined, {timeZone: audioState?.timezone || 'UTC'}); }
/* Allmon3 audio library and local-node play scheduler. */
let audioState = null;
let audioStack = [];
let audioRefreshing = false;
let audioVisible = false;
let audioControlBusy = false;
let audioMasterBusy = false;

function audioEl(id) { return document.getElementById(id); }

function audioMessage(message, error = false) {
	const element = audioEl('audio-feedback');
	element.textContent = message;
	element.className = error ? 'alert alert-danger' : message ? 'alert alert-info' : '';
}

async function audioAuthChanged() {
	if (!audioEl('audio-manager')) return;
	if (!loggedIn) {
		audioEl('audio-navigation').classList.add('d-none');
		audioEl('audio-manager').classList.add('d-none');
		audioVisible = false;
		audioState = null;
		audioEl('audio-preview').pause();
		audioEl('audio-preview').removeAttribute('src');
		return;
	}
	audioEl('audio-navigation').classList.remove('d-none');
	audioEl('audio-manager').classList.remove('d-none');
	if (!audioVisible) {
		audioVisible = true;
		await refreshAudioState();
	}
}

async function audioRequest(path, options) {
	const response = await fetch('master/audio/' + path, options);
	let result;
	try { result = await response.json(); }
	catch (_) { throw new Error('Audio service did not return a response'); }
	if (!response.ok || !result.SUCCESS) {
		throw new Error(result.ERROR || result.SECURITY || 'Audio request failed');
	}
	return result.SUCCESS;
}

async function refreshAudioState() {
	if (!loggedIn || audioRefreshing) return;
	audioRefreshing = true;
	try {
		audioState = await audioRequest('state');
		renderAudioState();
        if (typeof refreshAddonNodes === 'function') refreshAddonNodes();
        document.querySelectorAll('.audio-timezone').forEach(el => { el.textContent = audioState.timezone || 'UTC'; });
	} catch (e) {
		audioMessage(e.message, true);
	} finally {
		audioRefreshing = false;
	}
}

function audioOption(value, text) { return new Option(text, value); }

function audioLabel(ref) {
	if (ref === 'source:arn') return 'Amateur Radio Newsline (latest)';
	if (ref === 'source:aan') return 'ARRL Audio News (latest)';
	const asset = audioState?.assets.find(row => 'asset:' + row.id === ref);
	return asset ? asset.name : 'Missing file';
}

function audioButton(text, click, style = 'btn-outline-secondary') {
	const button = document.createElement('button');
	button.type = 'button';
	button.className = 'btn btn-sm ' + style;
	button.textContent = text;
	button.addEventListener('click', click);
	return button;
}

function renderAudioState() {
	const nodeSelect = audioEl('audio-node');
	const selectedNode = nodeSelect.value;
	nodeSelect.replaceChildren(...audioState.nodes.map(node => audioOption(String(node), String(node))));
	if (audioState.nodes.includes(Number(selectedNode))) nodeSelect.value = selectedNode;
	if (!audioState.nodes.length) audioMessage('No local Asterisk nodes are available for file playback.', true);

	const addSelect = audioEl('audio-add-item');
	const selectedItem = addSelect.value;
	addSelect.replaceChildren(
		audioOption('source:arn', 'Amateur Radio Newsline (latest)'),
		audioOption('source:aan', 'ARRL Audio News (latest)'),
		...audioState.assets.map(item => audioOption('asset:' + item.id, item.name))
	);
	if ([...addSelect.options].some(option => option.value === selectedItem)) addSelect.value = selectedItem;

	const sources = audioEl('audio-sources');
	sources.replaceChildren();
	for (const [key, name] of [['arn', 'Amateur Radio Newsline'], ['aan', 'ARRL Audio News']]) {
		const row = document.createElement('div');
		row.className = 'd-flex align-items-center justify-content-between gap-2 mb-2';
		const status = audioState.sources.find(item => item.source === key);
		const text = document.createElement('span');
		text.textContent = name + (status ? ' · edition ' + (status.edition_date || 'unverified') +
			' · fetched ' + audioDate(status.fetched_at) : ' · not collected');
		row.append(text, audioButton('Refresh', () => refreshNews(key)));
		sources.append(row);
	}

	const library = audioEl('audio-library');
	library.replaceChildren();
	for (const asset of audioState.assets) {
		const row = document.createElement('div');
		row.className = 'd-flex align-items-center justify-content-between gap-2 border-bottom py-1';
		const text = document.createElement('span');
		text.textContent = asset.name + ' · ' + Math.ceil(asset.seconds / 60) + ' min';
		row.append(text, audioButton('Preview', () => {
			const player = audioEl('audio-preview');
			player.src = 'master/audio/preview/' + asset.id;
			player.play().catch(() => {});
		}));
		library.append(row);
	}
	if (!audioState.assets.length) library.textContent = 'No audio has been uploaded or collected yet.';
	renderAudioStack();
	renderAudioSchedules();
	renderAudioJobs();
	renderAudioControls();
}

function addAudioItem() {
	const ref = audioEl('audio-add-item').value;
	if (ref && audioStack.length < 20) {
		audioStack.push(ref);
		renderAudioStack();
	} else audioMessage('A stack can contain up to 20 items.', true);
}

function renderAudioStack() {
    if (audioStack.length) {
        audioEl('audio-stack-validation').classList.add('d-none');
        audioEl('audio-add-item').classList.remove('is-invalid');
        audioEl('audio-add-item').removeAttribute('aria-invalid');
    }
	const list = audioEl('audio-stack');
	list.replaceChildren();
	audioStack.forEach((ref, index) => {
		const item = document.createElement('li');
		item.className = 'list-group-item d-flex align-items-center justify-content-between gap-2';
		const label = document.createElement('span');
		label.textContent = audioLabel(ref);
		const buttons = document.createElement('span');
		buttons.className = 'd-flex gap-1';
		const move = direction => {
			const other = index + direction;
			if (other >= 0 && other < audioStack.length) {
				[audioStack[index], audioStack[other]] = [audioStack[other], audioStack[index]];
				renderAudioStack();
			}
		};
		buttons.append(audioButton('↑', () => move(-1)), audioButton('↓', () => move(1)),
			audioButton('Remove', () => { audioStack.splice(index, 1); renderAudioStack(); }));
		item.append(label, buttons);
		list.append(item);
	});
	if (!audioStack.length) list.textContent = 'Add audio above to build a stack.';
}

function renderAudioSchedules() {
	const list = audioEl('audio-schedules');
	list.replaceChildren();
	for (const schedule of audioState.schedules) {
		const row = document.createElement('div');
		row.className = 'border rounded p-2 mb-2';
		const summary = document.createElement('span');
		const repeat = schedule.recurrence === 'daily' ? 'Daily at ' + schedule.local_time + ' ' + (audioState.timezone || 'UTC') + ' · ' : '';
		summary.textContent = schedule.name + ' · node ' + schedule.node + ' · ' + repeat +
			(schedule.enabled ? 'next ' + audioDate(schedule.next_at) : 'completed') +
			' · ' + schedule.items.map(audioLabel).join(' → ');
		row.append(summary, audioButton('Delete schedule', () => removeAudio('schedule', schedule.id), 'btn-outline-danger'));
		list.append(row);
	}
	if (!audioState.schedules.length) list.textContent = 'No schedules yet.';
}

function renderAudioJobs() {
	const list = audioEl('audio-jobs');
	list.replaceChildren();
	for (const job of audioState.jobs.slice(0, 12)) {
		const row = document.createElement('div');
		row.className = 'border rounded p-2 mb-2';
		const label = document.createElement('span');
		label.textContent = job.name + ' · node ' + job.node + ' · ' + job.status +
			' (' + job.position + '/' + job.items.length + ')' + (job.error ? ' · ' + job.error : '');
		row.append(label);
		if (job.status === 'pending') row.append(audioButton('Remove', () => removeAudio('job', job.id), 'btn-outline-danger'));
		list.append(row);
	}
	if (!audioState.jobs.length) list.textContent = 'Queue is empty.';
}

function selectedAudioNode() {
	const node = Number(audioEl('audio-node').value);
	if (!audioState?.nodes.includes(node)) throw new Error('Select a local playback node');
	return node;
}

async function audioChange(path, payload) {
	try {
		await audioRequest(path, { method: 'POST', headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(payload) });
		audioMessage('');
		await refreshAudioState();
	} catch (e) { audioMessage(e.message, true); }
}

async function uploadAudio() {
	try {
		const file = audioEl('audio-upload').files[0];
		if (!file) throw new Error('Choose an audio file');
		const form = new FormData();
		form.append('file', file);
		audioMessage('Uploading and converting audio...');
		await audioRequest('upload?node=' + selectedAudioNode(), { method: 'POST', body: form });
		audioEl('audio-upload').value = '';
		audioMessage('Audio is ready. Add it to a stack.');
		await refreshAudioState();
	} catch (e) { audioMessage(e.message, true); }
}

async function refreshNews(source) {
	try {
		audioMessage('Collecting and converting the latest bulletin...');
		await audioRequest('fetch', { method: 'POST', headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ node: selectedAudioNode(), source }) });
		audioMessage('Bulletin collected.');
		await refreshAudioState();
	} catch (e) { audioMessage(e.message, true); }
}

function audioStackPayload() {
	const name = audioEl('audio-stack-name').value.trim();
	if (!name || !audioStack.length) throw new Error('Name the stack and add at least one audio item');
	return { node: selectedAudioNode(), name, items: [...audioStack] };
}

async function queueAudio() {
	try { await audioChange('queue', audioStackPayload()); }
	catch (e) { audioMessage(e.message, true); }
}

function toggleAudioScheduleFields() {
	const recurrence = audioEl('audio-recurrence').value;
	for (const kind of ['once', 'daily', 'weekly']) {
		audioEl('audio-' + kind + '-fields').classList.toggle('d-none', recurrence !== kind);
	}
}

async function scheduleAudio() {
    if (!audioStack.length) {
        audioEl('audio-stack-validation').classList.remove('d-none');
        const selection = audioEl('audio-add-item');
        selection.classList.add('is-invalid');
        selection.setAttribute('aria-invalid', 'true');
        selection.focus();
        return;
    }
	try {
		const data = audioStackPayload();
		data.recurrence = audioEl('audio-recurrence').value;
		if (data.recurrence === 'daily') {
			data.local_time = audioEl('audio-daily-time').value;
			if (!data.local_time) throw new Error('Choose a daily time');
		} else if (data.recurrence === 'weekly') {
			data.weekday = Number(audioEl('audio-weekday').value);
			data.local_time = audioEl('audio-weekly-time').value;
		} else {
			const when = audioEl('audio-run-at').value;
			if (!when) throw new Error('Choose a date and time');
			data.run_at = when; // Interpreted in the advertised server timezone.
		}
		await audioChange('schedule', data);
	} catch (e) { audioMessage(e.message, true); }
}

async function removeAudio(kind, id) {
	try {
		await audioRequest(kind + '/' + id, { method: 'DELETE' });
		audioMessage(kind === 'job' ? 'Removed from queue.' : 'Schedule deleted.');
		await refreshAudioState();
	} catch (e) { audioMessage(e.message, true); }
}

setInterval(() => { if (audioVisible && !document.hidden) refreshAudioState(); }, 5000);

function activeAudioJob() {
    const node = Number(audioEl('audio-node').value);
    return audioState?.jobs.find(job => job.node === node &&
        ['playing', 'paused', 'pausing', 'stopping', 'control_failed'].includes(job.status));
}

async function toggleAudioMaster() {
    if (audioMasterBusy) return;
    const enabled = audioEl('audio-master-enabled').checked;
    audioMasterBusy = true;
    renderAudioControls();
    try {
        await audioRequest('enable', { method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ node: selectedAudioNode(), enabled }) });
        audioMessage('');
    } catch (e) { audioMessage(e.message, true); }
    finally {
        await refreshAudioState();
        audioMasterBusy = false;
        renderAudioControls();
    }
}

function renderAudioControls() {
    const enabled = audioState?.playback_enabled !== false;
    const master = audioEl('audio-master-enabled');
    if (!audioMasterBusy) master.checked = enabled;
    master.disabled = audioMasterBusy || !audioState?.can_manage_playback;
    master.title = 'Off blocks new playback and cancels queued jobs; the current job finishes. Scheduled starts while off are skipped.';
    audioEl('audio-queue').disabled = audioMasterBusy || !enabled || !audioState?.nodes.length;
    const job = activeAudioJob();
    const paused = job?.status === 'paused';
    const pause = audioEl('audio-pause');
    const stop = audioEl('audio-stop');
    pause.textContent = paused ? 'Resume' : 'Pause';
    pause.disabled = audioControlBusy || !job || !['playing', 'paused'].includes(job.status) || (paused && !enabled);
    stop.disabled = audioControlBusy || !job || ['pausing', 'stopping'].includes(job.status);
    audioEl('audio-playback-status').textContent = job ?
        job.name + ' · ' + job.status + (!enabled ? ' — master off; current job may finish.' : '') + (job.status === 'control_failed' ? ' — retry Stop to recover.' : '') :
        (enabled ? 'No active playback.' : 'Audio playback disabled. Scheduled starts are skipped.');
}

async function controlAudio(action) {
    if (audioControlBusy) return;
    const job = activeAudioJob();
    if (!job) return;
    if (action === 'pause' && job.status === 'paused') action = 'resume';
    audioControlBusy = true;
    renderAudioControls();
    try {
        await audioRequest(action, { method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ node: selectedAudioNode(), id: job.id }) });
        audioMessage(action === 'pause' ? 'Paused. Resume restarts the interrupted segment.' :
            action === 'resume' ? 'Playback resumed.' : 'Stopped. Current and queued jobs cancelled; future schedules unchanged.');
        await refreshAudioState();
    } catch (e) {
        audioMessage(e.message, true);
        await refreshAudioState();
    } finally {
        audioControlBusy = false;
        renderAudioControls();
    }
}

if (typeof registerAllmon3Addon === 'function') registerAllmon3Addon('announcements', {
    authChanged: audioAuthChanged,
    renderNode(node, slot) {
        if (!audioState?.nodes.includes(node)) return;
        const button = document.createElement('button');
        button.type = 'button'; button.className = 'btn btn-sm btn-outline-secondary';
        button.textContent = 'Announcements';
        button.addEventListener('click', () => {
            audioEl('audio-node').value = String(node); renderAudioControls();
            audioEl('audio-manager').open = true; audioEl('audio-manager').scrollIntoView();
        });
        slot.append(button);
    }
});
