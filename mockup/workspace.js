'use strict';
// Local, illustrative itinerary editing. No scoring API, persistence or publishing.
const workshop = {
  days: [
    ['beach', 'temple', 'market', 'lunch'],
    ['hoian', 'dinner'],
    ['museum', 'cafe']
  ],
  original: null,
  history: [],
  day: 0,
  selected: 'temple',
  filter: 'all',
  query: '',
  pane: 'map',
  mode: 'md',
  dragging: null,
  map: null,
};
workshop.original = structuredClone(workshop.days);
const workshopKinds = {
  sight: '관광',
  activity: '체험',
  rest: '휴식',
  meal: '식사'
};
const workshopCatalog = Object.keys(PLACES).filter(id => workshopKinds[PLACES[id].kind]);
const workshopChecks = '실제 보행 경로·계단·휴식 위치·영업시간을 확인하지 못했어요. 출발 전 관광지 공식 안내나 현지 여행사에 이동 가능 여부와 쉴 곳을 직접 확인해 주세요.';

function setRole(role) {
  document.querySelectorAll('.role-tab').forEach(button => {
    const active = button.id === `${role}-mode`;
    button.classList.toggle('active', active);
    button.setAttribute('aria-pressed', String(active));
  });
}
window.closeWorkspace = () => {
  workshop.map?.remove();
  workshop.map = null;
  workshop.dragging = null;
  setRole('customer');
};

function openWorkspace() {
  if (stage !== 'workspace') {
    workshop.customerStage = stage;
    workshop.customerStep = formStep;
    workshop.customerInputs = stage === 'form'
      ? [...document.querySelectorAll('#trip-form input, #trip-form select')].map(el => ({
          value: el.value,
          selected: el.tagName === 'SELECT' ? [...el.selectedOptions].map(option => option.value) : null,
        }))
      : null;
  }
  ++requestVersion;
  disposeMap();
  stage = 'workspace';
  workshop.mode = 'md';
  setRole('md');
  renderWorkspace();
  focusHeading();
}

function restoreCustomer() {
  ++requestVersion;
  window.closeWorkspace();
  if (workshop.customerStage === 'planner' && state) {
    stage = 'planner';
    renderPlanner();
  } else if (workshop.customerStage === 'form' && state) {
    stage = 'form';
    formStep = workshop.customerStep;
    renderForm();
    document.querySelectorAll('#trip-form input, #trip-form select').forEach((el, index) => {
      const saved = workshop.customerInputs?.[index];
      if (!saved) return;
      if (saved.selected) [...el.options].forEach(option => option.selected = saved.selected.includes(option.value));
      else el.value = saved.value;
      if (el.closest('.choice-field')) {
        el.nextElementSibling.querySelectorAll('[data-choice]').forEach(button => {
          const selected = [...el.selectedOptions].some(option => option.value === button.dataset.value);
          button.setAttribute('aria-pressed', String(selected));
          button.querySelector('.chip-tick').textContent = selected ? '✓' : '+';
        });
      }
    });
    updateChoiceSummary();
  } else landing();
  focusHeading();
}

function workshopMetrics(ids) {
  const meters = ids.reduce((sum, id) => sum + PLACES[id].meters, 0);
  const rest = ids.filter(id => ['rest', 'meal'].includes(PLACES[id].kind)).length;
  return {
    meters,
    rest,
    unknown: new Set(ids).size
  };
}

function workshopShelf() {
  const ids = workshopCatalog.filter(id => (workshop.filter === 'all' || PLACES[id].kind === workshop.filter) && `${PLACES[id].name} ${PLACES[id].desc}`.includes(workshop.query));
  return ids.map(id => {
    const p = PLACES[id],
      added = workshop.days[workshop.day].includes(id);
    return `<article class="shelf-place ${workshop.selected === id ? 'is-selected' : ''}" data-kind="${p.kind}" draggable="true" data-shelf="${id}"><div class="shelf-place-top"><span class="place-symbol" title="이 부분을 잡고 일정으로 끌어 놓으세요">${icon(p.icon, 24)}</span><span class="micro-label">${workshopKinds[p.kind]}</span><span class="unknown-tag">확인 전</span></div><button class="place-select" data-ws-select="${id}" aria-label="${esc(p.name)} 정보 보기"><strong>${p.name}</strong><span>${p.desc}</span></button><div class="shelf-place-bottom"><span>예시 보행 ${p.meters}m</span><button class="add-place" data-ws-add="${id}" ${added ? 'disabled' : ''} aria-label="${esc(p.name)} DAY ${workshop.day + 1}에 담기">${added ? '담김 ✓' : '+ 담기'}</button></div></article>`;
  }).join('') || '<p class="empty-shelf">조건에 맞는 장소가 없어요. 다른 검색어나 종류를 선택해 주세요.</p>';
}

function workshopBoard() {
  const ids = workshop.days[workshop.day];
  return `<div class="schedule-list" aria-label="DAY ${workshop.day + 1} 일정">${ids.map((id, i) => {
    const p = PLACES[id];
    return `<div class="insert-slot" data-ws-drop="${i}"><span>여기에 놓기</span></div><article class="schedule-card ${workshop.selected === id ? 'is-selected' : ''} ${p.kind === 'rest' ? 'is-rest' : ''}" data-kind="${p.kind}" draggable="true" data-ws-card="${i}"><div class="schedule-card-head"><span class="drag-handle" title="잡고 순서를 바꾸세요" aria-hidden="true">⠿</span><span class="schedule-order">${String(i + 1).padStart(2, '0')}</span><button class="place-select" data-ws-select="${id}" aria-label="${esc(p.name)} 정보 보기"><strong>${p.name}</strong><span>${workshopKinds[p.kind]} · 예시 체류 ${p.stay}분</span></button><span class="place-symbol">${icon(p.icon, 22)}</span></div><div class="schedule-card-meta"><span>${icon('walk', 13)} 예시 보행 ${p.meters}m</span><span class="unknown-tag">적합도 미확인</span></div><div class="schedule-controls"><button data-ws-up="${i}" ${i === 0 ? 'disabled' : ''} aria-label="${esc(p.name)} 위로">↑</button><button data-ws-down="${i}" ${i === ids.length - 1 ? 'disabled' : ''} aria-label="${esc(p.name)} 아래로">↓</button><label><span class="sr-only">${p.name} 이동할 날짜</span><select data-ws-move="${i}" aria-label="${esc(p.name)} 이동할 날짜"><option value="">날짜 이동</option>${workshop.days.map((_, d) => d !== workshop.day ? `<option value="${d}">DAY ${d + 1}</option>` : '').join('')}</select></label><button class="remove-stop" data-ws-remove="${i}" aria-label="${esc(p.name)} 일정에서 빼기">빼기</button></div></article>`;
  }).join('')}<div class="board-drop-end" data-ws-drop="${ids.length}">${icon('pin', 22)}<strong>${ids.length ? '다음 경험을 여기에' : '이 날의 첫 경험을 담아보세요'}</strong><span>장소 아이콘을 잡아 끌거나 ‘담기’를 누르세요.</span></div></div>`;
}

function renderWorkspace() {
  const focusLabel = document.activeElement?.getAttribute('aria-label');
  const focusId = document.activeElement?.id;
  workshop.map?.remove();
  workshop.map = null;
  const totalPlaces = workshop.days.reduce((sum, ids) => sum + ids.length, 0);
  const preview = workshop.mode === 'preview';
  const tools = preview
    ? '<button class="secondary" id="ws-back">← MD 편집으로</button>'
    : `<button class="secondary" id="ws-undo" ${!workshop.history.length ? 'disabled' : ''}>↶ 실행 취소</button><button class="primary" id="ws-preview">고객 미리보기 ↗</button>`;
  const body = preview ? renderWorkshopPreview() : renderWorkshopEditor();
  $('app').innerHTML = `<div class="workspace-page">
    <section class="workspace-heading"><div>
      <div class="eyebrow">${preview ? '고객용 여행 안내' : '여행사 · MD 작업실'}</div>
      <h1>${preview ? '다낭 · 호이안 여행 안내' : '다낭 · 호이안 일정 편집'}</h1>
      <p>${preview ? 'MD가 구성한 같은 일정을 고객의 시선으로 확인해요.' : '장소를 담고, 순서를 바꾸고. 여행의 흐름을 직접 만들어보세요.'}</p>
    </div><div class="workspace-tools">${tools}</div></section>
    <div class="studio-context"><span class="pill soft">다낭 · 호이안</span><span>${icon('calendar', 16)} 3일 일정 편집 예시</span><span>${icon('pin', 16)} ${totalPlaces}개 방문 일정</span><span class="context-status">● 평가 연결 전 · 화면 시연</span></div>
    ${body}
    <div class="studio-bottom-note">${icon('info', 16)} 편집 내용은 이 브라우저 화면에서만 유지돼요. 새로고침하면 초기화되며 상품 발행·예약·DB 저장은 하지 않아요.</div>
  </div>`;
  if (!preview && workshop.pane === 'map') initWorkshopMap();
  if (focusLabel || focusId) {
    const byId = focusId ? $(focusId) : null;
    const target = (byId && !byId.disabled ? byId : null)
      || [...document.querySelectorAll('[aria-label]')]
        .find(el => focusLabel && el.getAttribute('aria-label') === focusLabel && !el.disabled)
      || document.querySelector('.studio-days [aria-pressed="true"]');
    target?.focus({preventScroll: true});
  }
}

function renderWorkshopEditor() {
  const current = workshopMetrics(workshop.days[workshop.day]);
  const before = workshopMetrics(workshop.original[workshop.day]);
  const filters = Object.entries({all: '전체', sight: '관광', activity: '체험', rest: '휴식', meal: '식사'})
    .map(([key, label]) => `<button data-ws-filter="${key}" aria-pressed="${workshop.filter === key}">${label}</button>`).join('');
  const dayNames = ['다낭의 바다와 도시', '호이안에 등불이 켜지면', '여유를 담는 마지막 날'];
  const days = workshop.days.map((ids, day) => `<button data-ws-day="${day}" aria-pressed="${workshop.day === day}"><span>DAY ${String(day + 1).padStart(2, '0')}</span><strong>${dayNames[day]}</strong><small>${ids.length}개 일정 · 평가 미확인</small></button>`).join('');
  const pane = workshop.pane === 'map'
    ? '<div id="ws-map" aria-label="선택한 날짜의 장소 위치"></div><p class="map-disclaimer">점선은 방문 순서예요. 실제 보행 경로는 조회하지 않았어요.</p>'
    : renderWorkshopEvidence();
  return `<div class="studio-layout">
    <aside class="place-shelf">
      <div class="shelf-heading"><div><span class="small-label">01 · 장소 선택</span><h2>여행의 재료</h2></div><span>${workshopCatalog.length}곳</span></div>
      <label class="shelf-search"><span class="sr-only">장소 검색</span><input id="ws-search" type="search" placeholder="어떤 장소를 찾으세요?" value="${esc(workshop.query)}"></label>
      <div class="shelf-filters" aria-label="장소 종류">${filters}</div>
      <p class="shelf-hint">선택한 DAY ${workshop.day + 1}에 담겨요.</p>
      <div id="ws-shelf-items">${workshopShelf()}</div>
    </aside>
    <section class="schedule-board">
      <div class="board-heading"><div><span class="small-label">02 · 일정 편집</span><h2>여행을 펼쳐놓고</h2></div></div>
      <div class="editing-guide">${icon('pin', 20)}<div><strong>DAY ${workshop.day + 1}에 원하는 장소를 담아보세요.</strong><p>장소 아이콘을 잡아 일정 사이에 놓거나, ‘담기’를 누르세요. 순서와 날짜는 아래 버튼으로도 바꿀 수 있어요.</p></div></div>
      <nav class="studio-days" aria-label="편집할 날짜">${days}</nav>
      <div class="board-day-title"><h3>DAY ${workshop.day + 1}<span>${['바다와 사찰, 시장 사이', '등불을 기다리는 오후', '조금 더 느리게'][workshop.day]}</span></h3><span class="unknown-tag">검증 전 초안</span></div>
      <div id="ws-board-items">${workshopBoard()}</div>
    </section>
    <aside class="studio-inspector">
      <div class="inspector-tabs"><button data-ws-pane="map" aria-pressed="${workshop.pane === 'map'}">지도</button><button data-ws-pane="evidence" aria-pressed="${workshop.pane === 'evidence'}">장소·확인할 것</button></div>
      ${pane}
      <section class="studio-impact"><span class="small-label">03 · 변경 확인</span><h3>지금 배치의 변화</h3><dl>
        <div class="${before.meters !== current.meters ? 'metric-changed' : ''}"><dt>예시 보행량</dt><dd>${before.meters.toLocaleString()} → <strong>${current.meters.toLocaleString()}m</strong></dd></div>
        <div class="${before.rest !== current.rest ? 'metric-changed' : ''}"><dt>식사·휴식 일정</dt><dd>${before.rest} → <strong>${current.rest}개</strong></dd></div>
        <div><dt>부담도·상중하 평가</dt><dd>미확인 · 아직 판단하지 못했어요</dd></div>
      </dl><p>예시 거리의 합계예요. 장소 사이 이동·실제 휴식 가능 여부는 반영하지 못했어요.</p></section>
      <section class="verification-note"><strong>확인할 일이 남아 있어요</strong><p>${workshopChecks}</p></section>
    </aside>
  </div>`;
}

function renderWorkshopEvidence() {
  const p = PLACES[workshop.selected];
  return `<div class="studio-evidence"><span class="place-symbol large">${icon(p.icon,32)}</span><span class="small-label">PLACE NOTES</span><h3>${p.name}</h3><p>${p.desc}</p><dl><dt>거리·체류 시간</dt><dd>화면 시연용 가정값 · 외부 검수 전</dd><dt>확인하지 못한 정보</dt><dd>${p.unknown}</dd><dt>직접 확인할 것</dt><dd>공식 관광 안내나 현지 여행사에 ${p.unknown} 정보를 문의해 주세요.</dd><dt>부담 등급</dt><dd>미확인 · 평가 AI 연결 전</dd></dl></div>`;
}

function initWorkshopMap() {
  if (typeof L === 'undefined') {
    $('ws-map').textContent = '지도를 불러오지 못했어요. 일정 목록에서 장소를 확인해 주세요.';
    return;
  }
  const m = workshop.map = L.map('ws-map', {
    scrollWheelZoom: false,
    zoomAnimation: false,
    fadeAnimation: false,
    markerZoomAnimation: false
  }).setView([16.04, 108.25], 11);
  const layer = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 18,
    attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
  }).addTo(m);
  layer.on('tileerror', () => {
    const note = document.querySelector('.map-disclaimer');
    if (note) note.textContent = '지도 배경 연결이 원활하지 않아요. 표시한 점선은 실제 보행 경로가 아닌 방문 순서예요.';
  });
  const points = [];
  workshop.days[workshop.day].forEach((id, i) => {
    const p = PLACES[id],
      point = [p.lat, p.lng];
    points.push(point);
    const marker = L.marker(point, {
      title: p.name,
      icon: L.divIcon({
        className: 'studio-marker',
        html: `<span class="${id===workshop.selected?'selected':''}">${i+1}</span>`,
        iconSize: [32, 32]
      })
    }).addTo(m);
    marker.bindTooltip(p.name);
    marker.on('click', () => {
      workshop.selected = id;
      renderWorkspace();
    });
  });
  if (points.length > 1) {
    L.polyline(points, {
      color: '#7247bb',
      dashArray: '4 8',
      weight: 2
    }).addTo(m);
    m.fitBounds(points, {
      padding: [30, 30],
      maxZoom: 14,
      animate: false
    });
  } else if (points.length) m.setView(points[0], 13, {
    animate: false
  });
}

function renderWorkshopPreview() {
  return `<section class="preview-intro"><span class="small-label">CURATED FOR YOUR NEXT JOURNEY</span><h2>보고 싶은 마음은 그대로.<br>우리 가족의 속도로.</h2><p>여행사 기획자가 구성한 여행 초안이에요.<br>아직 가족별 적합도는 평가하지 못했어요.</p><button class="primary" id="ws-export">${icon('download',17)} 이 일정 안내서 저장</button></section><div class="preview-grid">${workshop.days.map((ids,d)=>`<section class="preview-day"><span class="small-label">DAY 0${d+1}</span><h3>${['다낭의 바다와 도시','호이안에 등불이 켜지면','여유를 담는 마지막 날'][d]}</h3><ol>${ids.map(id=>`<li>${icon(PLACES[id].icon,18)}<span><strong>${PLACES[id].name}</strong><small>${PLACES[id].desc}</small><small class="unknown-detail">미확인: ${PLACES[id].unknown}</small></span></li>`).join('')||'<li>아직 일정이 없어요.</li>'}</ol><p class="preview-day-foot">예시 보행 ${workshopMetrics(ids).meters.toLocaleString()}m · 적합도 미확인</p></section>`).join('')}</div><section class="verification-note"><strong>여행 전에 직접 확인해 주세요</strong><p>${workshopChecks}</p><p>표시된 일정·거리·체류 시간은 가정값이에요. 짧은 코스·실제 길찾기·가족별 부담도를 검증한 결과가 아니에요.</p></section>`;
}

function workshopChange(edit, message) {
  const before = JSON.stringify(workshop.days);
  edit();
  if (JSON.stringify(workshop.days) === before) return;
  workshop.history.push(JSON.parse(before));
  if (workshop.history.length > 30) workshop.history.shift();
  renderWorkspace();
  toast(message + ' 실제 경로와 적합도는 아직 미확인이에요.');
}

function workshopAdd(id, index = workshop.days[workshop.day].length) {
  if (!workshopCatalog.includes(id)) return;
  if (workshop.days[workshop.day].includes(id)) {
    toast('이 날에 이미 담긴 장소예요. 순서를 바꿔보세요.');
    return;
  }
  workshopChange(() => workshop.days[workshop.day].splice(index, 0, id), '장소를 일정에 담았어요.');
}

function workshopReorder(from, to) {
  const ids = workshop.days[workshop.day];
  if (!Number.isInteger(from) || from < 0 || from >= ids.length || to < 0 || to > ids.length) return;
  workshopChange(() => {
    const [id] = ids.splice(from, 1);
    ids.splice(to > from ? to - 1 : to, 0, id);
  }, '방문 순서를 바꿨어요.');
}

function workshopMove(index, day) {
  const ids = workshop.days[workshop.day];
  if (!Number.isInteger(day) || day < 0 || day >= workshop.days.length || !ids[index] || day === workshop.day) return;
  if (workshop.days[day].includes(ids[index])) {
    toast('도착 날짜에 이미 같은 장소가 있어요.');
    renderWorkspace();
    return;
  }
  workshopChange(() => {
    const [id] = ids.splice(index, 1);
    workshop.days[day].push(id);
  }, `DAY ${day+1}로 옮겼어요.`);
}

function exportWorkshop() {
  const html = `<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>반걸음 · 여행 초안</title><style>body{max-width:760px;margin:auto;padding:24px;font:18px/1.8 sans-serif;color:#292336}section{padding:20px 0;border-bottom:1px solid #ddd}small{display:block}aside{background:#fff5e5;padding:20px}</style><h1>다낭 · 호이안 여행 초안</h1><p>MD가 구성한 3일 일정 예시 · 실제 예약 내역이 아닙니다.</p>${workshop.days.map((ids,d)=>`<section><h2>DAY ${d+1}</h2><ol>${ids.map(id=>`<li>${esc(PLACES[id].name)}<small>미확인: ${esc(PLACES[id].unknown)}</small></li>`).join('')}</ol><p>예시 보행 ${workshopMetrics(ids).meters}m · 장소 사이 이동 제외</p></section>`).join('')}<aside><strong>적합도 미확인 · 여행 전에 직접 확인해 주세요</strong><p>${workshopChecks}</p><p>일정·거리·체류 시간은 가정값이며 가족별 부담도 평가 결과가 아닙니다.</p></aside></html>`;
  downloadFile('반걸음-MD-여행초안.html', html, 'text/html;charset=utf-8');
}
document.addEventListener('click', event => {
  const b = event.target.closest('button');
  if (!b || b.disabled) return;
  if (['md-mode', 'open-workspace'].includes(b.id)) return openWorkspace();
  if (b.id === 'customer-mode' && stage === 'workspace') return restoreCustomer();
  if (stage !== 'workspace') return;
  if (b.id === 'ws-undo') {
    const snapshot = workshop.history.pop();
    if (snapshot) {
      workshop.days = snapshot;
      renderWorkspace();
      toast('직전 편집을 되돌렸어요.');
    }
    return;
  }
  if (b.id === 'ws-preview') {
    workshop.mode = 'preview';
    renderWorkspace();
    focusHeading();
    return;
  }
  if (b.id === 'ws-back') {
    workshop.mode = 'md';
    renderWorkspace();
    focusHeading();
    return;
  }
  if (b.id === 'ws-export') return exportWorkshop();
  if (b.dataset.wsDay !== undefined) {
    workshop.day = Number(b.dataset.wsDay);
    renderWorkspace();
    return;
  }
  if (b.dataset.wsFilter) {
    workshop.filter = b.dataset.wsFilter;
    renderWorkspace();
    return;
  }
  if (b.dataset.wsPane) {
    workshop.pane = b.dataset.wsPane;
    renderWorkspace();
    return;
  }
  if (b.dataset.wsSelect) {
    workshop.selected = b.dataset.wsSelect;
    workshop.pane = 'evidence';
    renderWorkspace();
    return;
  }
  if (b.dataset.wsAdd) return workshopAdd(b.dataset.wsAdd);
  if (b.dataset.wsUp !== undefined) {
    const i = Number(b.dataset.wsUp);
    return workshopReorder(i, i - 1);
  }
  if (b.dataset.wsDown !== undefined) {
    const i = Number(b.dataset.wsDown);
    return workshopReorder(i, i + 2);
  }
  if (b.dataset.wsRemove !== undefined) return workshopChange(() => workshop.days[workshop.day].splice(Number(b.dataset.wsRemove), 1), '장소를 일정에서 뺐어요.');
});
document.addEventListener('input', event => {
  if (event.target.id === 'ws-search') {
    workshop.query = event.target.value;
    $('ws-shelf-items').innerHTML = workshopShelf();
  }
});
document.addEventListener('change', event => {
  if (event.target.dataset.wsMove !== undefined && event.target.value !== '') workshopMove(Number(event.target.dataset.wsMove), Number(event.target.value));
});
document.addEventListener('dragstart', event => {
  if (stage !== 'workspace' || workshop.mode !== 'md') return;
  if (event.target.closest('button,select,input')) {
    event.preventDefault();
    return;
  }
  const card = event.target.closest('[data-ws-card], [data-shelf]');
  if (!card) return;
  workshop.dragging = card.dataset.shelf ? {
    id: card.dataset.shelf
  } : {
    index: Number(card.dataset.wsCard),
    day: workshop.day
  };
  event.dataTransfer.setData('text/plain', '반걸음 장소');
  event.dataTransfer.effectAllowed = card.dataset.shelf ? 'copy' : 'move';
  card.classList.add('is-dragging');
  document.querySelector('.schedule-board')?.classList.add('is-dragging-over');
});
document.addEventListener('dragover', event => {
  const slot = event.target.closest('[data-ws-drop]');
  if (!slot || !workshop.dragging) return;
  event.preventDefault();
  event.dataTransfer.dropEffect = workshop.dragging.id ? 'copy' : 'move';
  document.querySelectorAll('.drop-target').forEach(el => el.classList.remove('drop-target'));
  slot.classList.add('drop-target');
});

function clearWorkshopDrag() {
  workshop.dragging = null;
  document.querySelectorAll('.drop-target,.is-dragging,.is-dragging-over').forEach(el => el.classList.remove('drop-target', 'is-dragging', 'is-dragging-over'));
}
document.addEventListener('drop', event => {
  const slot = event.target.closest('[data-ws-drop]'),
    drag = workshop.dragging;
  if (!slot || !drag) return;
  event.preventDefault();
  const to = Number(slot.dataset.wsDrop);
  clearWorkshopDrag();
  if (drag.id) workshopAdd(drag.id, to);
  else if (drag.day === workshop.day) workshopReorder(drag.index, to);
});
document.addEventListener('dragend', clearWorkshopDrag);
