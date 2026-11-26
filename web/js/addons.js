/* Optional package UI lifecycle and per-node embedding slots. */
const allmon3Addons = new Map();
function registerAllmon3Addon(id, addon) {
    allmon3Addons.set(id, addon);
    document.addEventListener('allmon3:auth', () => addon.authChanged?.());
    addon.authChanged?.();
    refreshAddonNodes();
}
function refreshAddonNodes() {
    document.querySelectorAll('.allmon3-node-addons').forEach(slot => {
        slot.replaceChildren();
        if (!loggedIn) return;
        const node = Number(slot.dataset.node);
        for (const addon of allmon3Addons.values()) addon.renderNode?.(node, slot);
    });
}
async function loadAllmon3Addons() {
    const response = await fetch('master/addons');
    if (!response.ok) throw new Error('Unable to load add-ins');
    for (const addon of (await response.json()).addons) {
        // Only installed same-origin add-in assets, never arbitrary remote scripts.
        for (const key of ['fragment', 'script', 'stylesheet']) {
            if (!/^addons\/[a-z][a-z0-9-]*\/[a-z][a-z0-9.-]*$/.test(addon[key])) throw new Error('Invalid add-in asset');
        }
        const fragment = await fetch(addon.fragment);
        if (!fragment.ok) continue;
        const host = document.createElement('section');
        host.innerHTML = await fragment.text(); // Package-owned static markup.
        document.getElementById('allmon3-addons').append(host);
        const css = document.createElement('link'); css.rel = 'stylesheet'; css.href = addon.stylesheet; document.head.append(css);
        await new Promise((resolve, reject) => {
            const script = document.createElement('script'); script.src = addon.script;
            script.onload = resolve; script.onerror = reject; document.body.append(script);
        });
    }
}
document.addEventListener('DOMContentLoaded', () => {
    loadAllmon3Addons().catch(error => console.error('Allmon3 add-ins:', error));
});
