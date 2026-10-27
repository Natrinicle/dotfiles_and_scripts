// LinkedIn Voyager in-page fetch. Paste as chrome__use_browser eval payload.
// Set threadId. Do not put regex character classes in this file — MCP JSON
// encoding of eval JS turns ^ inside /[^;]/ into SyntaxError: Unexpected token '^'.
(async () => {
  const csrf = (document.cookie.split(';').map(s => s.trim()).find(s => s.startsWith('JSESSIONID=')) || '').slice('JSESSIONID='.length).replace(/"/g, '');
  const threadId = 'THREAD_ID_WITH_EQUALS_UNENCODED';
  const cut = 0; // prior archive last createdAt ms, or 0 for a full pull
  const headers = {
    'accept': 'application/vnd.linkedin.normalized+json+2.1',
    'csrf-token': csrf,
    'x-restli-protocol-version': '2.0.0',
    'x-li-lang': 'en_US'
  };
  const textOf = (obj) => {
    if (!obj) return '';
    if (typeof obj === 'string') return obj.trim();
    if (Array.isArray(obj)) return obj.map(textOf).filter(Boolean).join('\n');
    if (typeof obj === 'object') {
      if (typeof obj.text === 'string') return obj.text.trim();
      for (const k of ['attributedBody', 'body', 'commentary', 'fallback', 'title']) {
        const g = textOf(obj[k]);
        if (g) return g;
      }
    }
    return '';
  };
  const miniName = (mini) => {
    const first = (mini && mini.firstName) || '';
    const last = (mini && mini.lastName) || '';
    return (first + ' ' + last).trim() || (mini && mini.publicIdentifier) || 'Unknown';
  };
  const indexIncluded = (data) => {
    const out = {};
    for (const item of (data.included || [])) {
      if (!item || typeof item !== 'object') continue;
      if (item.entityUrn) out[item.entityUrn] = item;
      if (item.$id) out[item.$id] = item;
    }
    return out;
  };
  const resolveSender = (event, included) => {
    const fromRef = event['*from'] || event.from;
    if (typeof fromRef === 'string') {
      const member = included[fromRef] || {};
      const miniRef = member['*miniProfile'] || member.miniProfile;
      if (typeof miniRef === 'string') return miniName(included[miniRef] || {});
      if (miniRef && typeof miniRef === 'object') return miniName(miniRef);
      return miniName(member);
    }
    return 'Unknown';
  };
  const parseEvent = (event, included) => {
    const content = event.eventContent || {};
    const msg = content['com.linkedin.voyager.messaging.event.MessageEvent'] || content;
    let body = textOf(msg.attributedBody || msg.body);
    const notes = [];
    const att = msg.attachments || [];
    if (att.length) notes.push('attachments:' + att.length);
    const custom = msg.customContent;
    if (custom && typeof custom === 'object') {
      const inner = Object.values(custom)[0];
      const extra = textOf(inner);
      if (extra && extra !== body) body = body ? (body + '\n' + extra) : extra;
      notes.push('custom:' + Object.keys(custom).join(','));
    }
    return {
      createdAt: event.createdAt,
      sender: resolveSender(event, included),
      body,
      notes,
      reactions: event.reactionSummaries || [],
      attMeta: (msg.attachments || []).map(a => ({name: a.name || a.mediaType, mediaType: a.mediaType})),
      customKeys: custom && typeof custom === 'object' ? Object.keys(custom) : []
    };
  };
  const all = [];
  const seen = new Set();
  let createdBefore = null;
  const pages = [];
  for (let page = 0; page < 50; page++) {
    let url = 'https://www.linkedin.com/voyager/api/messaging/conversations/' + threadId + '/events?count=20';
    if (createdBefore) url += '&createdBefore=' + createdBefore;
    const r = await fetch(url, {credentials: 'include', headers});
    if (r.status !== 200) {
      pages.push({page, status: r.status, nNew: 0});
      break;
    }
    const data = await r.json();
    const included = indexIncluded(data);
    const events = (data.included || []).filter(item => item && (item.$type === 'com.linkedin.voyager.messaging.Event' || String(item.entityUrn || '').startsWith('urn:li:messagingMessage:') || item.eventContent));
    const timestamps = [];
    let nNew = 0;
    for (const ev of events) {
      const urn = ev.entityUrn;
      if (seen.has(urn)) continue;
      seen.add(urn);
      all.push(parseEvent(ev, included));
      nNew++;
      if (ev.createdAt) timestamps.push(ev.createdAt);
    }
    pages.push({page, status: r.status, nNew, nIncluded: (data.included || []).length});
    if (!timestamps.length || nNew === 0) break;
    const oldest = Math.min.apply(null, timestamps);
    if (createdBefore != null && oldest >= createdBefore) break;
    createdBefore = oldest;
  }
  all.sort((a, b) => (a.createdAt || 0) - (b.createdAt || 0));
  window.__liThread = {n: all.length, messages: all, pages};
  const newer = all.filter(m => (m.createdAt || 0) > cut);
  return JSON.stringify({
    n: all.length,
    csrfOk: csrf.slice(0, 5),
    pages,
    first: all[0] && all[0].createdAt,
    last: all.length && all[all.length - 1].createdAt,
    nNewer: newer.length,
    newer,
    last5: all.slice(-5).map(m => ({createdAt: m.createdAt, sender: m.sender, body: (m.body || '').slice(0, 240), notes: m.notes}))
  });
})()
